"""
SIH26034 — LMPC Compliance Engine: FastAPI Application

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
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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
                    rule_reference=v.get("rule_reference", "Rule 6 - LM(PC) Rules, 2011"),
                    act_section=v.get("act_section", "Section 18(1) - Legal Metrology Act, 2009"),
                    punishment_section=v.get("punishment_section", "Section 36(1) - Legal Metrology Act, 2009"),
                    statutory_penalty=v.get("statutory_penalty"),
                    legal_proof_summary=v.get("legal_proof_summary"),
                    field_name=v.get("field_name", "Declaration"),
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
    logger.info("🏛️ SIH26034 LMPC Compliance Engine starting...")
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
    title="SIH26034 — LMPC Compliance Engine",
    description=(
        "Automated verification of mandatory declarations on pre-packaged "
        "commodities under the Legal Metrology (Packaged Commodities) Rules, 2011. "
        "Supports physical packaging image scanning and e-commerce URL auditing."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "*",
    ],
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
        "service": "LMPC Compliance Engine",
        "model": settings.GEMINI_MODEL,
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Audit Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/audit/image")
async def audit_image(file: UploadFile = File(...)):
    """
    Audit a packaging image for LMPC compliance.
    """
    if file.content_type not in {
        "image/jpeg", "image/png", "image/webp", "image/jpg"
    }:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Accepted: JPEG, PNG, WebP.",
        )

    image_bytes = await file.read()

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 20 MB.")

    logger.info("📸 Image audit request: %s (%d bytes)", file.filename, len(image_bytes))

    try:
        result = await run_image_audit(image_bytes=image_bytes)

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        # Persist audit record and generate report
        audit_id = await persist_audit_result(
            result=result,
            input_type="image",
        )
        result["audit_id"] = audit_id
        result["report_url"] = f"/api/report/html/{audit_id}"

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Image audit failed")
        raise HTTPException(status_code=500, detail=str(e))


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

    if not image_bytes or len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="No image provided. Send file or image_base64.")

    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Max 20 MB.")

    logger.info("📱 Live scan request: %d bytes, barcode=%s", len(image_bytes), barcode or "(auto-detect)")

    try:
        result = await run_image_audit(image_bytes=image_bytes)

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        # If barcode was pre-decoded by the frontend, inject it into extractions
        if barcode and result.get("extractions"):
            existing_barcode = result["extractions"].get("barcode_number")
            if not existing_barcode or (
                isinstance(existing_barcode, dict) and not existing_barcode.get("value")
            ):
                result["extractions"]["barcode_number"] = {
                    "value": barcode,
                    "confidence": 0.99,
                }

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
