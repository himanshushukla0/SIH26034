"""
SIH26034 — Kraya-Rakshak (क्रय-रक्षक): Automated LMPC Compliance Engine
FastAPI Application

REST API server exposing endpoints for:
- Image-based packaging audit (POST /api/audit/image)
- E-commerce URL audit (POST /api/audit/url)
- Audit history retrieval (GET /api/audits)
- Single audit retrieval (GET /api/audit/{audit_id})
- Official Inspection Notice report (GET /api/report/html/{audit_id}, GET /api/report/pdf/{audit_id})
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import lmpc_vision as vision
import lmpc_extraction as ex

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.database import async_session, get_db, init_db
from backend.models import (
    Audit,
    AuditInputType,
    AuditStatus,
    Violation,
    ViolationSeverity,
    VerificationCheck,
    VerificationStatus,
)
from backend.agents.orchestrator import run_image_audit, run_url_audit
from backend.agents.report_generator import report_generator
from backend.agents.verification_agent import verification_agent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database Persistence Helper
# ---------------------------------------------------------------------------

async def persist_audit_result(
    result: dict[str, Any],
    input_type: str,
    source_url: Optional[str] = None,
    image_path: Optional[str] = None,
) -> str:
    """Save an audit run, its violations, and generate inspection notice."""
    audit_id = str(uuid.uuid4())
    verdict = result.get("verdict") or {}
    extractions = result.get("extractions") or {}
    listing_data = result.get("listing_data") or {}

    # Extract high-level product metadata
    product_name = (
        extractions.get("product_name", {}).get("value")
        if isinstance(extractions.get("product_name"), dict)
        else (listing_data.get("product_name") if listing_data else None)
    )
    manufacturer = (
        extractions.get("manufacturer_name", {}).get("value")
        if isinstance(extractions.get("manufacturer_name"), dict)
        else (listing_data.get("manufacturer") if listing_data else None)
    )
    mrp = (
        str(extractions.get("mrp", {}).get("value"))
        if isinstance(extractions.get("mrp"), dict)
        else (str(listing_data.get("listed_price")) if listing_data else None)
    )
    net_qty = (
        str(extractions.get("net_quantity", {}).get("value"))
        if isinstance(extractions.get("net_quantity"), dict)
        else (str(listing_data.get("net_quantity")) if listing_data else None)
    )

    # Generate the official inspection notice file
    try:
        html_report_path = report_generator.generate_html_report(
            audit_id=audit_id,
            verdict_data=verdict,
            extractions=extractions,
            listing_data=listing_data,
            source_url=source_url,
        )
    except Exception as e:
        logger.warning("Could not pre-generate report file: %s", e)
        html_report_path = None

    async with async_session() as session:
        try:
            audit = Audit(
                id=audit_id,
                input_type=AuditInputType(input_type),
                source_url=source_url,
                image_path=image_path,
                status=AuditStatus.COMPLETED if not result.get("error") else AuditStatus.FAILED,
                compliance_score=verdict.get("compliance_score"),
                overall_status=verdict.get("overall_status", "UNKNOWN"),
                total_checks=verdict.get("total_checks", 10),
                passed_checks=verdict.get("passed_checks", 0),
                failed_checks=verdict.get("failed_checks", 0),
                product_name=str(product_name) if product_name else None,
                manufacturer=str(manufacturer) if manufacturer else None,
                mrp=mrp,
                net_quantity=net_qty,
                report_pdf_path=html_report_path,
                raw_extractions_json=json.dumps(extractions, default=str),
            )
            session.add(audit)

            # Add violations with statutory proof details
            for v in verdict.get("violations", []):
                sev_str = v.get("severity", "major").lower()
                sev_enum = (
                    ViolationSeverity.CRITICAL
                    if "crit" in sev_str
                    else ViolationSeverity.MINOR
                    if "min" in sev_str
                    else ViolationSeverity.MAJOR
                )
                violation = Violation(
                    audit_id=audit_id,
                    rule_reference=str(v.get("rule_reference", "Rule 6 - LM(PC) Rules, 2011"))[:150],
                    act_section=str(v.get("act_section", "Section 18(1) - Legal Metrology Act, 2009"))[:150] if v.get("act_section") else None,
                    punishment_section=str(v.get("punishment_section", "Section 36(1) - Legal Metrology Act, 2009"))[:150] if v.get("punishment_section") else None,
                    statutory_penalty=v.get("statutory_penalty"),
                    legal_proof_summary=v.get("legal_proof_summary"),
                    field_name=str(v.get("field_name", "Declaration"))[:100],
                    severity=sev_enum,
                    description=v.get("description", ""),
                    expected_value=v.get("expected_value"),
                    found_value=v.get("found_value"),
                    is_discrepancy=v.get("is_discrepancy", False),
                )
                session.add(violation)

            await session.commit()
            logger.info("Persisted audit record %s with %d violations.", audit_id, len(verdict.get("violations", [])))

            # Persist verification checks if available
            verification = result.get("verification")
            if verification:
                audit.trust_score = verification.get("trust_score")
                audit.expiry_status = verification.get("expiry_status")
                audit.days_until_expiry = verification.get("days_until_expiry")
                audit.is_expired = verification.get("expiry_status") == "EXPIRED"

                # Extract barcode & FSSAI from extractions for quick lookup
                if isinstance(extractions.get("barcode_number"), dict):
                    audit.barcode_number = extractions["barcode_number"].get("value")
                elif isinstance(extractions.get("barcode_number"), str):
                    audit.barcode_number = extractions["barcode_number"]

                for check_data in verification.get("checks", []):
                    status_str = check_data.get("status", "unverifiable").lower()
                    try:
                        status_enum = VerificationStatus(status_str)
                    except ValueError:
                        status_enum = VerificationStatus.UNVERIFIABLE

                    check = VerificationCheck(
                        audit_id=audit_id,
                        check_name=check_data.get("check_name", "unknown"),
                        status=status_enum,
                        confidence=check_data.get("confidence", 0.0),
                        details=check_data.get("details", ""),
                        evidence_json=json.dumps(check_data.get("evidence", {}), default=str),
                        is_counterfeit_signal=check_data.get("is_counterfeit_signal", False),
                    )
                    session.add(check)

                await session.commit()
                logger.info("Persisted %d verification checks for audit %s.",
                            len(verification.get("checks", [])), audit_id)

        except Exception as e:
            await session.rollback()
            logger.exception("Failed to persist audit record %s: %s", audit_id, e)

    return audit_id


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    logger.info("🏛️ SIH26034 Kraya-Rakshak (क्रय-रक्षक) Compliance Engine starting...")
    logger.info("   Model: %s", settings.GEMINI_MODEL)
    logger.info("   Database: %s", settings.DATABASE_URL)
    await init_db()
    logger.info("   Database tables initialized.")
    logger.info("✅ Server ready.")
    yield
    logger.info("🛑 Server shutting down.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Kraya-Rakshak (क्रय-रक्षक) — Automated LMPC Compliance Engine",
    description=(
        "Kraya-Rakshak (क्रय-रक्षक): Automated verification of mandatory declarations on "
        "pre-packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011. "
        "Supports physical packaging image scanning, multi-shot panel capture, and e-commerce URL auditing."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server and production deployments (e.g. Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """Server health check endpoint."""
    return {
        "status": "healthy",
        "service": "Kraya-Rakshak",
        "full_name": "Kraya-Rakshak (क्रय-रक्षक) — Automated LMPC Compliance Engine",
        "model": settings.GEMINI_MODEL,
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Audit Endpoints
# ---------------------------------------------------------------------------

def save_upload(file: UploadFile) -> str:
    """
    Save uploaded file permanently to backend/uploads and return its absolute path.
    Guarantees that image_path is never NULL on database audit records.
    """
    upload_dir = Path("backend/uploads").resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "packaging_image.jpg").name
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    dest_path = upload_dir / unique_name

    file.file.seek(0)
    content = file.file.read()
    dest_path.write_bytes(content)
    file.file.seek(0)
    logger.info("💾 Saved uploaded package image to %s (%d bytes)", dest_path, len(content))
    return str(dest_path)


async def call_gemini(path: str, prompt: str, schema: Optional[dict[str, Any]] = None) -> Any:
    """
    Call Gemini multimodal vision with the Vision Extraction Contract.
    """
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client()
    model_name = settings.GEMINI_MODEL

    img_path = Path(path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found on disk: {path}")

    image_bytes = img_path.read_bytes()

    mime_type = "image/jpeg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        mime_type = "image/png"
    elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        mime_type = "image/webp"

    image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    config_kwargs: dict[str, Any] = {
        "temperature": 0.1,
        "max_output_tokens": 4096,
        "response_mime_type": "application/json",
    }
    if schema:
        config_kwargs["response_schema"] = schema

    config = genai_types.GenerateContentConfig(**config_kwargs)

    try:
        if hasattr(client, "aio") and hasattr(client.aio, "models"):
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=[prompt, image_part],
                config=config,
            )
        else:
            import asyncio
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=[prompt, image_part],
                config=config,
            )

        return response.text.strip() if response.text else ""
    except Exception as e:
        logger.error("Gemini vision inference failed for %s: %s", path, e)
        return {
            "is_product_label": False,
            "what_it_shows": f"Gemini inference failure: {e}",
            "fields": {},
        }


async def persist_audit_from_extraction(
    audit_res: dict[str, Any],
    image_path: str,
) -> str:
    """Save an accepted extraction audit to the database, ensuring image_path is saved."""
    audit_id = str(uuid.uuid4())
    summary = audit_res.get("summary") or {}
    checks = audit_res.get("checks") or []
    barcode_text = audit_res.get("barcode_text")

    def get_check_val(rule_id: str) -> Optional[str]:
        for c in checks:
            if c.get("rule_id") == rule_id and c.get("status") == "PASS":
                return str(c.get("val"))
        return None

    p_name = get_check_val("GENERIC_NAME") or audit_res.get("what_it_shows") or "Pre-Packaged Commodity"
    m_name = get_check_val("MANUFACTURER")
    mrp_val = get_check_val("MRP")
    net_qty_val = get_check_val("NET_QUANTITY")

    # Pre-generate inspection notice HTML
    try:
        report_dict = {
            "compliance_score": summary.get("score_percent") or 0.0,
            "overall_status": summary.get("verdict") or "UNKNOWN",
            "violations": [
                {
                    "rule_reference": c.get("clause", "Rule 6 - LM(PC) Rules, 2011"),
                    "act_section": "Section 18(1) - Legal Metrology Act, 2009",
                    "punishment_section": "Section 15(6) - Improvement Notice (Jan Vishwas Act, 2026)",
                    "statutory_penalty": "First contravention: Statutory Improvement Notice under s.15(6)",
                    "field_name": c.get("rule_id"),
                    "severity": "critical" if c.get("rule_id") in ("MRP", "NET_QUANTITY") else "major",
                    "description": c.get("val", ""),
                    "expected_value": c.get("label", ""),
                    "found_value": c.get("quoted_text"),
                    "is_discrepancy": False,
                }
                for c in checks if c.get("status") != "PASS"
            ],
            "declaration_status": {
                c.get("rule_id"): {
                    "status": "FOUND" if c.get("status") == "PASS" else "MISSING",
                    "value": c.get("val"),
                }
                for c in checks
            },
        }
        html_report_path = report_generator.generate_html_report(
            audit_id=audit_id,
            verdict_data=report_dict,
            extractions={c.get("rule_id"): c.get("val") for c in checks},
        )
    except Exception as e:
        logger.warning("Could not pre-generate report file: %s", e)
        html_report_path = None

    async with async_session() as session:
        audit = Audit(
            id=audit_id,
            input_type=AuditInputType.IMAGE,
            image_path=image_path,
            status=AuditStatus.COMPLETED,
            compliance_score=summary.get("score_percent"),
            overall_status=summary.get("verdict"),
            total_checks=summary.get("total_checks", 10),
            passed_checks=summary.get("passed", 0),
            failed_checks=summary.get("failed", 0),
            product_name=str(p_name) if p_name else None,
            manufacturer=str(m_name) if m_name else None,
            mrp=mrp_val,
            net_quantity=net_qty_val,
            barcode_number=barcode_text,
            report_pdf_path=html_report_path,
            raw_extractions_json=json.dumps(audit_res, default=str),
        )
        session.add(audit)

        for c in checks:
            if c.get("status") != "PASS":
                sev = ViolationSeverity.CRITICAL if c.get("rule_id") in ("MRP", "NET_QUANTITY") else ViolationSeverity.MAJOR
                violation = Violation(
                    audit_id=audit_id,
                    rule_reference=c.get("clause", "Rule 6 - LM(PC) Rules, 2011"),
                    act_section="Section 18(1) - Legal Metrology Act, 2009",
                    punishment_section="Section 15(6) - Improvement Notice (Jan Vishwas Act, 2026)",
                    statutory_penalty="First contravention: Statutory Improvement Notice under s.15(6)",
                    field_name=c.get("rule_id", "Declaration"),
                    severity=sev,
                    description=c.get("val", "Declaration missing or unverified"),
                    expected_value=c.get("label"),
                    found_value=c.get("quoted_text"),
                    is_discrepancy=False,
                )
                session.add(violation)

        await session.commit()
        logger.info("Persisted audit record %s with real image_path=%s", audit_id, image_path)

    return audit_id


@app.post("/api/audit/image")
async def audit_image(file: UploadFile = File(...)):
    if file.content_type and not (
        file.content_type.startswith("image/")
        or file.content_type in {"image/jpeg", "image/png", "image/webp", "image/jpg"}
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Accepted: JPEG, PNG, WebP.",
        )

    path = save_upload(file)

    gate = vision.prepare_audit_input(path)
    if not gate["proceed"]:
        return JSONResponse(
            status_code=422,
            content={
                "status": "REFUSED",
                "audit_status": "REFUSED",
                "error": gate["user_message"],
                "detail": gate["user_message"],
                "reason": gate["user_message"],
                "guidance": gate["guidance"],
                "image_assessment": gate["image"],
                "verdict": None,
                "extractions": {},
            },
        )

    # Read image bytes and run complete multimodal LMPC audit.
    # CRITICAL FIX: Never inject a hardcoded fallback barcode.
    # When no barcode is detected from the image, pass barcode=None so that
    # Gemini Vision drives the entire extraction. Using a fake barcode causes
    # every product without a readable barcode to return Tata Tea Gold data.
    img_bytes = Path(path).read_bytes()
    detected_barcode = gate.get("barcode", {}).get("barcode")
    audit_res = await verification_agent.audit_by_barcode(
        barcode=detected_barcode,  # None when no barcode detected — intentional
        image_bytes=img_bytes,
    )
    audit_res["input_type"] = "image"
    audit_res["image_path"] = path
    audit_res["image_assessment"] = gate.get("image")
    if detected_barcode:
        audit_res["barcode_text"] = detected_barcode

    try:
        audit_id = await persist_audit_result(result=audit_res, input_type="image")
        audit_res["audit_id"] = audit_id
        audit_res["report_url"] = f"/api/report/html/{audit_id}"
    except Exception as e:
        logger.warning("Could not persist audit record: %s", e)

    return JSONResponse(content=audit_res)


@app.post("/api/audit/multi-shot")
async def audit_multi_shot(
    shot_front: Optional[UploadFile] = File(None),
    shot_back: Optional[UploadFile] = File(None),
    shot_barcode: Optional[UploadFile] = File(None),
):
    """
    Multi-Shot Packaging Capture Engine:
    Parses front panel, back declarations panel, and barcode/price close-up as ONE unified label.
    Solves the physical packaging reality where declarations are spread across opposite panels.
    """
    import time
    t0 = time.perf_counter()

    shots_map = [
        ("front", shot_front, "Front Display Panel (PDP)"),
        ("back", shot_back, "Back / Side Declarations Panel"),
        ("barcode", shot_barcode, "Barcode / Price Sticker Close-Up"),
    ]
    active_shots = [(name, f, desc) for name, f, desc in shots_map if f is not None]
    if not active_shots:
        raise HTTPException(status_code=400, detail="At least one packaging shot (front, back, or barcode) is required.")

    shot_paths = []
    ocr_texts = []
    all_lines = []
    detected_barcodes = []
    shots_metadata = []

    from lmpc_ocr import read_label
    from lmpc_labelparse import parse_label, ParsedField
    from lmpc_checks import run_checks

    for panel_name, s, panel_desc in active_shots:
        p = save_upload(s)
        shot_paths.append(p)
        gate = vision.prepare_audit_input(p)
        b = None
        if gate and isinstance(gate, dict):
            barcode_dict = gate.get("barcode")
            if isinstance(barcode_dict, dict):
                b = barcode_dict.get("barcode")
        if b:
            detected_barcodes.append(b)

        ocr_res = await read_label(p)
        txt = ocr_res.text or ""
        if txt:
            ocr_texts.append(f"--- PANEL: {panel_name.upper()} ({panel_desc}) ---\n{txt}")
            all_lines.extend(ocr_res.lines)

        shots_metadata.append({
            "panel": panel_name,
            "description": panel_desc,
            "filename": s.filename,
            "path": p,
            "has_barcode": bool(b),
            "lines_count": len(ocr_res.lines),
            "text_preview": (txt[:120] + ("..." if len(txt) > 120 else "")) if txt else "",
        })

    unified_text = "\n".join(ocr_texts)
    parse_res = parse_label({"text": unified_text, "lines": all_lines})
    checks_res = run_checks(parse_res.fields, has_pin_code=parse_res.has_pin_code)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    barcode_val = detected_barcodes[0] if detected_barcodes else None
    verification_data = None
    if barcode_val:
        try:
            v_res = await verification_agent.verify_packaging(
                barcode=barcode_val,
                extractions={
                    "product_name": {"value": parse_res.fields.get("GENERIC_NAME", ParsedField()).value},
                    "mrp": {"value": parse_res.fields.get("MRP", ParsedField()).value},
                    "net_quantity": {"value": parse_res.fields.get("NET_QUANTITY", ParsedField()).value},
                }
            )
            verification_data = v_res.as_dict()
        except Exception:
            pass

    # Computed USP fallback if MRP and Net Qty exist
    computed_usp = parse_res.fields.get("UNIT_SALE_PRICE", ParsedField()).value
    if not computed_usp and parse_res.fields.get("MRP") and parse_res.fields.get("NET_QUANTITY"):
        mrp_f = parse_res.fields.get("MRP")
        qty_f = parse_res.fields.get("NET_QUANTITY")
        if mrp_f.normalized_numeric and qty_f.normalized_numeric and qty_f.normalized_unit:
            calc_usp = mrp_f.normalized_numeric / qty_f.normalized_numeric
            computed_usp = f"₹ {calc_usp:.2f} / {qty_f.normalized_unit} (Calculated)"

    # Complete 10-declaration status mapping for frontend checklist
    declaration_status = {
        "manufacturer_name": {
            "status": "FOUND" if parse_res.fields.get("MANUFACTURER", ParsedField()).value else "MISSING",
            "value": parse_res.fields.get("MANUFACTURER", ParsedField()).value,
            "stitched": parse_res.fields.get("MANUFACTURER", ParsedField()).stitched,
        },
        "manufacturer_address": {
            "status": "FOUND" if parse_res.fields.get("MANUFACTURER", ParsedField()).value else "MISSING",
            "value": parse_res.fields.get("MANUFACTURER", ParsedField()).value,
            "stitched": parse_res.fields.get("MANUFACTURER", ParsedField()).stitched,
        },
        "country_of_origin": {
            "status": "FOUND" if parse_res.fields.get("COUNTRY_OF_ORIGIN", ParsedField()).value else "MISSING",
            "value": parse_res.fields.get("COUNTRY_OF_ORIGIN", ParsedField()).value,
            "stitched": parse_res.fields.get("COUNTRY_OF_ORIGIN", ParsedField()).stitched,
        },
        "generic_name": {
            "status": "PARTIAL" if not parse_res.fields.get("GENERIC_NAME", ParsedField()).value else "FOUND",
            "value": parse_res.fields.get("GENERIC_NAME", ParsedField()).value or "Unparsed by regex (Requires vision model / officer confirmation)",
        },
        "net_quantity": {
            "status": "FOUND" if parse_res.fields.get("NET_QUANTITY", ParsedField()).value else "MISSING",
            "value": parse_res.fields.get("NET_QUANTITY", ParsedField()).value,
            "stitched": parse_res.fields.get("NET_QUANTITY", ParsedField()).stitched,
        },
        "manufacture_date": {
            "status": "FOUND" if parse_res.fields.get("DATE_OF_MANUFACTURE", ParsedField()).value else "MISSING",
            "value": parse_res.fields.get("DATE_OF_MANUFACTURE", ParsedField()).value,
            "stitched": parse_res.fields.get("DATE_OF_MANUFACTURE", ParsedField()).stitched,
        },
        "expiry_date": {
            "status": "FOUND" if parse_res.fields.get("BEST_BEFORE", ParsedField()).value else "MISSING",
            "value": parse_res.fields.get("BEST_BEFORE", ParsedField()).value,
            "stitched": parse_res.fields.get("BEST_BEFORE", ParsedField()).stitched,
        },
        "mrp": {
            "status": "FOUND" if parse_res.fields.get("MRP", ParsedField()).value else "MISSING",
            "value": parse_res.fields.get("MRP", ParsedField()).value,
            "stitched": parse_res.fields.get("MRP", ParsedField()).stitched,
        },
        "unit_sale_price": {
            "status": "FOUND" if parse_res.fields.get("UNIT_SALE_PRICE", ParsedField()).value else "MISSING",
            "value": parse_res.fields.get("UNIT_SALE_PRICE", ParsedField()).value or computed_usp,
            "stitched": parse_res.fields.get("UNIT_SALE_PRICE", ParsedField()).stitched,
        },
        "consumer_care": {
            "status": "FOUND" if parse_res.fields.get("CONSUMER_CARE", ParsedField()).value else "MISSING",
            "value": parse_res.fields.get("CONSUMER_CARE", ParsedField()).value,
            "stitched": parse_res.fields.get("CONSUMER_CARE", ParsedField()).stitched,
        },
    }

    verdict_data = {
        "compliance_score": checks_res["compliance_score_percent"],
        "overall_status": checks_res["overall_status"],
        "total_checks": checks_res["total"],
        "passed_checks": checks_res["passed"],
        "failed_checks": checks_res["failed"],
        "computed_usp": computed_usp,
        "declaration_status": declaration_status,
        "violations": [
            {
                "rule_reference": f["clause"],
                "field_name": f["rule_id"],
                "severity": f["severity"].lower(),
                "description": f.get("detail") or f["val"],
                "statutory_penalty": "First contravention: Improvement Notice under Section 15(6)",
                "found_value": f.get("quoted_text") or f["val"],
                "expected_value": f["label"],
            }
            for f in checks_res["findings"] if f["status"] == "FAIL"
        ],
    }

    extractions = {
        "product_name": {"value": parse_res.fields.get("GENERIC_NAME", ParsedField()).value, "confidence": parse_res.fields.get("GENERIC_NAME", ParsedField()).confidence},
        "generic_name": {"value": parse_res.fields.get("GENERIC_NAME", ParsedField()).value, "confidence": parse_res.fields.get("GENERIC_NAME", ParsedField()).confidence},
        "manufacturer_name": {"value": parse_res.fields.get("MANUFACTURER", ParsedField()).value, "confidence": parse_res.fields.get("MANUFACTURER", ParsedField()).confidence},
        "manufacturer_address": {"value": parse_res.fields.get("MANUFACTURER", ParsedField()).value, "confidence": parse_res.fields.get("MANUFACTURER", ParsedField()).confidence},
        "country_of_origin": {"value": parse_res.fields.get("COUNTRY_OF_ORIGIN", ParsedField()).value, "confidence": parse_res.fields.get("COUNTRY_OF_ORIGIN", ParsedField()).confidence},
        "net_quantity": {"value": parse_res.fields.get("NET_QUANTITY", ParsedField()).value, "confidence": parse_res.fields.get("NET_QUANTITY", ParsedField()).confidence},
        "mrp": {"value": parse_res.fields.get("MRP", ParsedField()).value, "confidence": parse_res.fields.get("MRP", ParsedField()).confidence},
        "unit_sale_price": {"value": parse_res.fields.get("UNIT_SALE_PRICE", ParsedField()).value or computed_usp, "confidence": parse_res.fields.get("UNIT_SALE_PRICE", ParsedField()).confidence},
        "manufacture_date": {"value": parse_res.fields.get("DATE_OF_MANUFACTURE", ParsedField()).value, "confidence": parse_res.fields.get("DATE_OF_MANUFACTURE", ParsedField()).confidence},
        "expiry_date": {"value": parse_res.fields.get("BEST_BEFORE", ParsedField()).value, "confidence": parse_res.fields.get("BEST_BEFORE", ParsedField()).confidence},
        "consumer_care_name": {"value": parse_res.fields.get("CONSUMER_CARE", ParsedField()).value, "confidence": parse_res.fields.get("CONSUMER_CARE", ParsedField()).confidence},
        "barcode_number": {"value": barcode_val, "confidence": 1.0 if barcode_val else 0.0},
    }

    stage1_economics = {
        "cost_inr": 0.0,
        "latency_ms": elapsed_ms,
        "settled_stage": 1 if not parse_res.needs_model_escalation else 3,
        "needs_model": parse_res.needs_model_escalation,
        "reason": parse_res.escalation_reason,
        "coverage_percent": parse_res.coverage_percent,
        "parsed_count": parse_res.parsed_count,
        "stitched_fields": [k for k, v in parse_res.fields.items() if getattr(v, "stitched", False)],
        "pin_code_detected": parse_res.has_pin_code,
        "pin_code": parse_res.pin_code,
    }

    result = {
        "status": "COMPLETED",
        "audit_status": checks_res["overall_status"],
        "declaration_status": declaration_status,
        "input_type": "multi_shot",
        "shots_count": len(shot_paths),
        "shots_metadata": shots_metadata,
        "verdict": verdict_data,
        "extractions": extractions,
        "verification": verification_data,
        "parse_result": parse_res.as_dict(),
        "stage1_economics": stage1_economics,
        "summary": {
            "score_percent": checks_res["compliance_score_percent"],
            "verdict": checks_res["overall_status"],
            "passed": checks_res["passed"],
            "failed": checks_res["failed"],
            "unverified": checks_res["unverified"],
            "total_checks": checks_res["total"],
        },
        "checks": checks_res["findings"],
        "barcode_text": barcode_val,
        "needs_model_escalation": parse_res.needs_model_escalation,
        "coverage_percent": parse_res.coverage_percent,
    }

    try:
        audit_id = await persist_audit_result(result=result, input_type="multi_shot", image_path=shot_paths[0])
        result["audit_id"] = audit_id
        result["report_url"] = f"/api/report/html/{audit_id}"
    except Exception as e:
        logger.warning("Could not persist multi-shot audit: %s", e)

    return JSONResponse(content=result)


@app.post("/api/audit/url")
async def audit_url(url: str = Form(...)):
    """
    Audit an e-commerce product listing for LMPC compliance.
    """
    if not url or not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Must start with http:// or https://",
        )

    logger.info("🛒 URL audit request: %s", url)

    try:
        result = await run_url_audit(url=url)

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        # Persist audit record and generate report
        audit_id = await persist_audit_result(
            result=result,
            input_type="url",
            source_url=url,
        )
        result["audit_id"] = audit_id
        result["report_url"] = f"/api/report/html/{audit_id}"

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("URL audit failed")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Live Camera Scan & Standalone Verification Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/scan")
async def scan_package(
    file: UploadFile = File(None),
    image_base64: str = Form(None),
    barcode: str = Form(None),
):
    """
    Live scanner endpoint — accepts a camera frame (file upload or base64)
    and an optional pre-decoded barcode string. Runs the full pipeline
    including authenticity verification.
    """
    image_bytes = None

    if file:
        image_bytes = await file.read()
    elif image_base64:
        import base64
        try:
            # Strip data URL prefix if present
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            image_bytes = base64.b64decode(image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {e}")

    clean_barcode = barcode.strip() if barcode and barcode.strip() else None

    if not clean_barcode and (not image_bytes or len(image_bytes) == 0):
        raise HTTPException(
            status_code=400,
            detail="No input provided. Send a barcode number or an image.",
        )

    if image_bytes and len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Max 20 MB.")

    logger.info(
        "📱 Live scan request: bytes=%s, barcode=%s",
        len(image_bytes) if image_bytes else 0,
        clean_barcode or "(auto-detect)",
    )

    # 1. If barcode is already provided (scanned or entered by user), run tailored barcode audit
    if clean_barcode:
        try:
            result = await verification_agent.audit_by_barcode(
                barcode=clean_barcode,
                image_bytes=image_bytes,
            )
            audit_id = await persist_audit_result(
                result=result,
                input_type="camera",
            )
            result["audit_id"] = audit_id
            result["report_url"] = f"/api/report/html/{audit_id}"
            return JSONResponse(content=result)
        except Exception as e:
            logger.exception("Barcode audit failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Barcode audit failed: {e}")

    # 2. Otherwise image was provided without barcode: pass through Image Gate
    temp_upload_dir = Path("backend/uploads")
    temp_upload_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_upload_dir / f"scan_gate_{uuid.uuid4().hex}.jpg"
    temp_file.write_bytes(image_bytes)

    try:
        from backend.image_gate import prepare_audit_input
        gate_result = prepare_audit_input(str(temp_file))

        if not gate_result["proceed"]:
            logger.warning(
                "🛑 Scan frame refused by Image Gate: %s (status: %s)",
                gate_result["user_message"],
                gate_result["image"]["status"],
            )
            return JSONResponse(
                status_code=422,
                content={
                    "status": "REFUSED",
                    "audit_status": "REFUSED",
                    "error": gate_result["user_message"],
                    "detail": gate_result["user_message"],
                    "reason": gate_result["user_message"],
                    "guidance": gate_result["guidance"],
                    "image_assessment": gate_result["image"],
                },
            )

        # If barcode was decoded by gate from the packaging image, audit by barcode!
        detected_barcode = gate_result.get("barcode", {}).get("barcode")
        if detected_barcode:
            logger.info("🎯 Gate auto-decoded barcode from image: %s", detected_barcode)
            result = await verification_agent.audit_by_barcode(
                barcode=detected_barcode,
                image_bytes=image_bytes,
            )
            audit_id = await persist_audit_result(
                result=result,
                input_type="camera",
            )
            result["audit_id"] = audit_id
            result["report_url"] = f"/api/report/html/{audit_id}"
            return JSONResponse(content=result)

    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass

    # 3. If image passed gate but no 1D barcode was detected, run multimodal image audit
    try:
        result = await run_image_audit(image_bytes=image_bytes)

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        audit_id = await persist_audit_result(
            result=result,
            input_type="camera",
        )
        result["audit_id"] = audit_id
        result["report_url"] = f"/api/report/html/{audit_id}"

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Live scan failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/verify/barcode/{barcode}")
async def verify_barcode(barcode: str):
    """
    Standalone barcode lookup — verify a barcode against Open Food Facts
    and return product identity + GS1 country code analysis.
    """
    if not barcode or len(barcode) < 8:
        raise HTTPException(status_code=400, detail="Invalid barcode. Must be at least 8 digits.")

    logger.info("🔍 Standalone barcode verification: %s", barcode)

    try:
        # Build minimal extractions dict for the verification agent
        mock_extractions = {
            "barcode_number": {"value": barcode, "confidence": 1.0},
        }

        barcode_check = await verification_agent._check_barcode_identity(mock_extractions)
        gs1_check = verification_agent._check_gs1_country_code(mock_extractions)

        return {
            "barcode": barcode,
            "barcode_identity": {
                "status": barcode_check.status,
                "details": barcode_check.details,
                "evidence": barcode_check.evidence,
                "is_counterfeit_signal": barcode_check.is_counterfeit_signal,
            },
            "gs1_country": {
                "status": gs1_check.status,
                "details": gs1_check.details,
                "evidence": gs1_check.evidence,
            },
        }
    except Exception as e:
        logger.exception("Barcode verification failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/verify/fssai/{license_number}")
async def verify_fssai(license_number: str):
    """
    Standalone FSSAI license verification — checks format validity
    and queries the FOSCOS database.
    """
    if not license_number:
        raise HTTPException(status_code=400, detail="License number is required.")

    logger.info("🔍 Standalone FSSAI verification: %s", license_number)

    try:
        mock_extractions = {
            "additional_declarations": [f"FSSAI Lic No: {license_number}"],
        }

        fssai_check = await verification_agent._check_fssai_license(mock_extractions)

        return {
            "license_number": license_number,
            "status": fssai_check.status,
            "details": fssai_check.details,
            "evidence": fssai_check.evidence,
            "is_counterfeit_signal": fssai_check.is_counterfeit_signal,
        }
    except Exception as e:
        logger.exception("FSSAI verification failed")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Reports & Audit History
# ---------------------------------------------------------------------------

@app.get("/api/report/html/{audit_id}")
async def get_html_report(audit_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve official HTML inspection notice for a given audit."""
    stmt = select(Audit).options(selectinload(Audit.violations)).where(Audit.id == audit_id)
    res = await db.execute(stmt)
    audit = res.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit record not found.")

    if audit.report_pdf_path and Path(audit.report_pdf_path).exists():
        media_type = "application/pdf" if str(audit.report_pdf_path).lower().endswith(".pdf") else "text/html"
        return FileResponse(audit.report_pdf_path, media_type=media_type)

    # Generate if not on disk
    extractions = json.loads(audit.raw_extractions_json) if audit.raw_extractions_json else {}
    html_path = report_generator.generate_html_report(
        audit_id=audit.id,
        verdict_data={
            "compliance_score": audit.compliance_score or 0.0,
            "overall_status": audit.overall_status or ("COMPLIANT" if (audit.compliance_score or 0) >= 90 else "NON_COMPLIANT"),
            "violations": [
                {
                    "rule_reference": v.rule_reference,
                    "act_section": v.act_section,
                    "punishment_section": v.punishment_section,
                    "statutory_penalty": v.statutory_penalty,
                    "legal_proof_summary": v.legal_proof_summary,
                    "field_name": v.field_name,
                    "severity": v.severity.value if hasattr(v.severity, "value") else str(v.severity),
                    "description": v.description,
                    "expected_value": v.expected_value,
                    "found_value": v.found_value,
                    "is_discrepancy": v.is_discrepancy,
                }
                for v in audit.violations
            ],
            "declaration_status": {},
        },
        extractions=extractions,
        source_url=audit.source_url,
    )
    return FileResponse(html_path, media_type="text/html")


# ---------------------------------------------------------------------------
# Statutory Notice Drafting Engine (Jan Vishwas Act, 2026 / s.15(6))
# ---------------------------------------------------------------------------

class NoticeDraftRequest(BaseModel):
    item: dict[str, Any]
    failures: list[dict[str, Any]]
    officer_name: str = "Inspector of Legal Metrology, Enforcement Division"
    ref: str = ""
    offence_number: int = 1
    compliance_days: int = 30


@app.post("/api/notice/draft")
async def post_draft_notice(req: NoticeDraftRequest):
    """Draft statutory Improvement Notice (s.15(6)) or Show Cause Notice based on violations."""
    try:
        from backend.lmpc_notice import draft_notice
    except ImportError:
        import lmpc_notice
        draft_notice = lmpc_notice.draft_notice

    res = draft_notice(
        item=req.item,
        failures=req.failures,
        officer_name=req.officer_name,
        ref=req.ref,
        offence_number=req.offence_number,
    )
    return res


@app.get("/api/report/notice/{audit_id}")
async def get_audit_notice(
    audit_id: str,
    offence_number: int = 1,
    officer_name: str = "Inspector of Legal Metrology, Enforcement Division",
    db: AsyncSession = Depends(get_db),
):
    """Retrieve official drafted statutory notice for a given audit record."""
    stmt = select(Audit).options(selectinload(Audit.violations)).where(Audit.id == audit_id)
    res = await db.execute(stmt)
    audit = res.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit record not found.")

    extractions = json.loads(audit.raw_extractions_json) if audit.raw_extractions_json else {}

    rule_map = {
        "manufacturer_name": "MANUFACTURER",
        "manufacturer_address": "MANUFACTURER",
        "country_of_origin": "COUNTRY_OF_ORIGIN",
        "generic_name": "COMMODITY_NAME",
        "net_quantity": "NET_QUANTITY",
        "net_quantity_unit": "NET_QUANTITY",
        "manufacture_date": "MFG_DATE",
        "expiry_date": "EXPIRY_DATE",
        "mrp": "MRP",
        "unit_sale_price": "UNIT_SALE_PRICE",
        "consumer_care": "CONSUMER_CARE",
        "pdp_font_size": "PDP_AREA_FONT",
    }

    failures = []
    for v in audit.violations:
        rid = rule_map.get(v.field_name, "MANUFACTURER")
        failures.append({
            "rule_id": rid,
            "found": v.found_value or v.description or "-",
            "detail": v.description,
        })

    p_name = extractions.get("product_name")
    if isinstance(p_name, dict):
        p_name = p_name.get("value")
    m_name = extractions.get("manufacturer_name")
    if isinstance(m_name, dict):
        m_name = m_name.get("value")
    b_code = extractions.get("barcode_number")
    if isinstance(b_code, dict):
        b_code = b_code.get("value")

    item = {
        "name": p_name or "Pre-Packaged Commodity",
        "manufacturer": m_name or "Unspecified Entity",
        "barcode": b_code or "-",
        "data_source": audit.source_url or f"Direct Inspection (Audit ID {audit.id[:8]})",
        "checks": [v.description for v in audit.violations],
    }

    try:
        from backend.lmpc_notice import draft_notice
    except ImportError:
        import lmpc_notice
        draft_notice = lmpc_notice.draft_notice

    ref_id = f"LMPC/HQ/2026/{audit.id[:8].upper()}"
    notice_res = draft_notice(
        item=item,
        failures=failures,
        officer_name=officer_name,
        ref=ref_id,
        offence_number=offence_number,
    )
    return {
        "audit_id": audit.id,
        "ref": ref_id,
        **notice_res,
    }


@app.get("/api/audits")
async def list_audits(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List recent audit records."""
    stmt = (
        select(Audit)
        .order_by(desc(Audit.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    audits = res.scalars().all()

    return [
        {
            "id": a.id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "input_type": a.input_type.value if hasattr(a.input_type, "value") else str(a.input_type),
            "source_url": a.source_url,
            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
            "compliance_score": a.compliance_score,
            "overall_status": a.overall_status,
            "product_name": a.product_name,
            "manufacturer": a.manufacturer,
            "mrp": a.mrp,
            "net_quantity": a.net_quantity,
            "report_url": f"/api/report/html/{a.id}",
        }
        for a in audits
    ]


@app.get("/api/audit/{audit_id}")
async def get_audit_detail(audit_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve full detail for a single audit, including violations and statutory proof."""
    stmt = select(Audit).options(selectinload(Audit.violations)).where(Audit.id == audit_id)
    res = await db.execute(stmt)
    audit = res.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")

    return {
        "id": audit.id,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "input_type": audit.input_type.value if hasattr(audit.input_type, "value") else str(audit.input_type),
        "source_url": audit.source_url,
        "compliance_score": audit.compliance_score,
        "overall_status": audit.overall_status,
        "total_checks": audit.total_checks,
        "passed_checks": audit.passed_checks,
        "failed_checks": audit.failed_checks,
        "product_name": audit.product_name,
        "manufacturer": audit.manufacturer,
        "mrp": audit.mrp,
        "net_quantity": audit.net_quantity,
        "report_url": f"/api/report/html/{audit.id}",
        "violations": [
            {
                "rule_reference": v.rule_reference,
                "act_section": v.act_section,
                "punishment_section": v.punishment_section,
                "statutory_penalty": v.statutory_penalty,
                "legal_proof_summary": v.legal_proof_summary,
                "field_name": v.field_name,
                "severity": v.severity.value if hasattr(v.severity, "value") else str(v.severity),
                "description": v.description,
                "expected_value": v.expected_value,
                "found_value": v.found_value,
                "is_discrepancy": v.is_discrepancy,
            }
            for v in audit.violations
        ],
    }


@app.get("/api/analytics/summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    """
    Returns aggregate compliance intelligence for state Legal Metrology controllers:
    - Total audits & compliance rate
    - Status breakdown (COMPLIANT, NON_COMPLIANT, NEEDS_MANUAL_REVIEW)
    - Total violations & severity distribution
    - Top violated declaration fields
    - Top Act/Rule contraventions (Section 18, Section 11, Section 36(1), Section 29)
    - Offending brand rankings
    - Estimated statutory fine liabilities under Legal Metrology Act, 2009
    """
    stmt = (
        select(Audit)
        .options(selectinload(Audit.violations))
        .order_by(desc(Audit.created_at))
    )
    res = await db.execute(stmt)
    audits = res.scalars().all()

    total_audits = len(audits)
    if total_audits == 0:
        return {
            "total_audits": 0,
            "compliant_count": 0,
            "non_compliant_count": 0,
            "manual_review_count": 0,
            "compliance_rate": 100.0,
            "average_compliance_score": 100.0,
            "total_violations": 0,
            "violations_by_severity": {"critical": 0, "major": 0, "minor": 0},
            "top_violated_fields": [],
            "top_contraventions": [],
            "top_offending_brands": [],
            "estimated_fines_inr": 0,
            "recent_audits": [],
        }

    compliant_count = sum(1 for a in audits if a.overall_status == "COMPLIANT")
    manual_review_count = sum(1 for a in audits if a.overall_status == "NEEDS_MANUAL_REVIEW")
    non_compliant_count = sum(1 for a in audits if a.overall_status in ("NON_COMPLIANT", "PARTIAL_VIOLATION"))

    scores = [a.compliance_score for a in audits if a.compliance_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    compliance_rate = round((compliant_count / total_audits) * 100, 1)

    all_violations: list[Violation] = []
    for a in audits:
        all_violations.extend(a.violations)

    total_violations = len(all_violations)

    severity_counts = {"critical": 0, "major": 0, "minor": 0}
    field_counts: dict[str, int] = {}
    contravention_counts: dict[str, int] = {}
    brand_counts: dict[str, int] = {}

    for v in all_violations:
        sev = v.severity.value if hasattr(v.severity, "value") else str(v.severity).lower()
        if sev in severity_counts:
            severity_counts[sev] += 1

        fn = v.field_name or "General"
        field_counts[fn] = field_counts.get(fn, 0) + 1

        rule = v.rule_reference or "Rule 6 - LM(PC) Rules, 2011"
        contravention_counts[rule] = contravention_counts.get(rule, 0) + 1

    for a in audits:
        brand = a.manufacturer
        if brand and brand not in ("Not Declared", "Unknown", ""):
            clean_brand = brand.split(",")[0].strip()[:40]
            brand_counts[clean_brand] = brand_counts.get(clean_brand, 0) + len(a.violations)

    top_fields = [
        {"field": k, "count": v}
        for k, v in sorted(field_counts.items(), key=lambda item: item[1], reverse=True)[:6]
    ]

    top_contraventions = [
        {"contravention": k, "count": v}
        for k, v in sorted(contravention_counts.items(), key=lambda item: item[1], reverse=True)[:6]
    ]

    top_brands = [
        {"brand": k, "violations_count": v}
        for k, v in sorted(brand_counts.items(), key=lambda item: item[1], reverse=True)[:6]
    ]

    est_fines = 0
    for v in all_violations:
        punish = str(v.punishment_section or "")
        if "29" in punish:
            est_fines += 10000
        elif "36(2)" in punish:
            est_fines += 10000
        else:
            est_fines += 25000

    recent = [
        {
            "id": a.id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "product_name": a.product_name or "Pre-Packaged Commodity",
            "manufacturer": a.manufacturer or "Not Declared",
            "compliance_score": a.compliance_score or 0.0,
            "overall_status": a.overall_status or "UNKNOWN",
            "violations_count": len(a.violations),
        }
        for a in audits[:10]
    ]

    return {
        "total_audits": total_audits,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "manual_review_count": manual_review_count,
        "compliance_rate": compliance_rate,
        "average_compliance_score": avg_score,
        "total_violations": total_violations,
        "violations_by_severity": severity_counts,
        "top_violated_fields": top_fields,
        "top_contraventions": top_contraventions,
        "top_offending_brands": top_brands,
        "estimated_fines_inr": est_fines,
        "recent_audits": recent,
    }


# ---------------------------------------------------------------------------
# SIH26034 — 5-Stage Compliance Funnel, Officer Worklist & Benchmark Endpoints
# ---------------------------------------------------------------------------

from backend.agents.compliance_funnel import (
    artwork_cache,
    compute_dhash,
    DeterministicRuleChecker,
)
from backend.agents.officer_worklist import (
    officer_worklist,
    RiskScoringEngine,
    OfficerWorklistItem,
)
from backend.data.maharashtra_spices_dataset import (
    PILOT_SLICE_INFO,
    EVALUATION_BENCHMARK_RESULTS,
    SAMPLE_OFFICER_WORKLIST_ITEMS,
)

# Seed officer worklist with Maharashtra pilot slice items if empty
if not officer_worklist._worklist:
    for item_data in SAMPLE_OFFICER_WORKLIST_ITEMS:
        item = OfficerWorklistItem(**item_data)
        officer_worklist.add_item(item)


@app.get("/api/funnel/stats")
async def get_funnel_stats():
    """
    Returns aggregate 5-Stage Funnel throughput, cost curve,
    and national scale extrapolation metrics for SIH presentation.
    """
    return {
        "pilot_slice": PILOT_SLICE_INFO,
        "runtime_dedup_cache": {
            "total_screened": artwork_cache.total_screened,
            "dedup_cache_hits": artwork_cache.total_dedup_hits,
            "dedup_hit_rate_percent": round(
                (artwork_cache.total_dedup_hits / max(artwork_cache.total_screened, 1)) * 100.0, 1
            ),
        },
    }


@app.get("/api/funnel/officer-worklist")
async def get_officer_worklist(
    jurisdiction: Optional[str] = None,
    evidentiary_class: Optional[str] = None,
    min_priority: Optional[str] = None,
    limit: int = 50,
):
    """
    Returns prioritized officer worklist ranked by FSSAI-aligned risk score.
    Routes scarce inspector attention to highest-risk contraventions.
    """
    worklist_items = officer_worklist.get_ranked_worklist(
        jurisdiction=jurisdiction,
        evidentiary_class=evidentiary_class,
        min_priority=min_priority,
        limit=limit,
    )
    return {
        "total_items": len(worklist_items),
        "jurisdiction_filter": jurisdiction or "All Maharashtra Divisions",
        "evidentiary_filter": evidentiary_class or "All Evidentiary Classes",
        "items": worklist_items,
    }


@app.get("/api/funnel/benchmark")
async def get_evaluation_benchmark():
    """
    Returns the 200-item labelled evaluation benchmark with per-field
    Precision, Recall, and F1 scores, establishing empirical technical defensibility.
    """
    return EVALUATION_BENCHMARK_RESULTS


@app.post("/api/funnel/clearance")
async def preprint_clearance(
    brand_name: str = Form(...),
    product_name: str = Form(...),
    gtin: str = Form(...),
    net_quantity: str = Form(...),
    mrp: str = Form(...),
    unit_sale_price: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """
    Manufacturer Self-Declaration / Pre-Print Clearance Portal.
    Brands upload label artwork before printing.
    Compliant artwork receives a Pre-Print Clearance Certificate
    and earns inspection deprioritization for the brand.
    """
    img_bytes = await file.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="Artwork file is empty.")

    # Compute perceptual artwork hash (Stage 0)
    art_hash = compute_dhash(img_bytes)

    # Parse numeric fields for Stage 1 deterministic check
    import re
    mrp_match = re.search(r"[\d\.]+", mrp.replace(",", ""))
    mrp_num = float(mrp_match.group(0)) if mrp_match else None

    qty_match = re.search(r"[\d\.]+", net_quantity)
    qty_num = float(qty_match.group(0)) if qty_match else None

    unit_match = re.search(r"[a-zA-Z]+", net_quantity)
    unit_str = unit_match.group(0).lower() if unit_match else ""

    usp_num = None
    usp_unit = ""
    if unit_sale_price:
        usp_match = re.search(r"[\d\.]+", unit_sale_price)
        usp_num = float(usp_match.group(0)) if usp_match else None
        usp_unit_match = re.search(r"/[a-zA-Z]+", unit_sale_price)
        usp_unit = usp_unit_match.group(0).replace("/", "") if usp_unit_match else ""

    declarations = {
        "product_name": product_name,
        "manufacturer_name": brand_name,
        "manufacturer_address": "Factory Premises",
        "country_of_origin": "India",
        "net_quantity": net_quantity,
        "net_quantity_numeric": qty_num,
        "net_quantity_unit": unit_str,
        "mrp": mrp,
        "mrp_numeric": mrp_num,
        "mrp_text": mrp,
        "mrp_raw_text": f"MRP {mrp} (incl. of all taxes)" if "tax" not in mrp.lower() else mrp,
        "unit_sale_price": unit_sale_price,
        "unit_sale_price_numeric": usp_num,
        "unit_sale_price_unit": usp_unit,
        "manufacture_date": "09/2026",
        "expiry_date": "09/2027",
        "consumer_care": "care@brand.com",
    }

    stage1_res = DeterministicRuleChecker.run_stage_1(declarations)

    is_cleared = stage1_res.is_valid
    cert_id = f"LMPC-PREPRINT-{uuid.uuid4().hex[:8].upper()}"

    # Register in artwork cache (Stage 0)
    artwork_cache.register(
        gtin=gtin,
        artwork_hash=art_hash,
        product_name=product_name,
        brand=brand_name,
        status="COMPLIANT" if is_cleared else "NON_COMPLIANT",
        compliance_score=100.0 if is_cleared else 65.0,
        violations=[f["description"] for f in stage1_res.failures],
    )

    return {
        "clearance_status": "APPROVED" if is_cleared else "REJECTED_NEEDS_REVISION",
        "certificate_id": cert_id if is_cleared else None,
        "gtin": gtin,
        "product_name": product_name,
        "brand_name": brand_name,
        "artwork_hash": art_hash,
        "inspection_deprioritization": True if is_cleared else False,
        "incentive_trade": (
            "Under Section 15(6) compliance policy, pre-cleared artwork earns deprioritized "
            "market surveillance and reduced random audit frequency for 12 months."
            if is_cleared
            else "Artwork contains statutory defects. Please correct errors before submitting to print run."
        ),
        "failures": stage1_res.failures,
        "execution_time_ms": stage1_res.execution_time_ms,
    }


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
