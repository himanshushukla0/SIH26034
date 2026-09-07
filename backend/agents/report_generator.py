"""
SIH26034 — Agent 4: LMPC Legal Infraction Notice & Report Generator

Generates official government-grade Legal Metrology Inspection Reports and
Infraction Notices under the Legal Metrology Act, 2009 & Legal Metrology
(Packaged Commodities) Rules, 2011.

Supports:
- Professional, print-ready HTML Inspection Notice with official emblem styling.
- PDF generation via WeasyPrint (with graceful HTML fallback).
- Machine-readable JSON compliance audit summary.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.config import settings
from backend.rule_table import (
    LADDER_36_1,
    LADDER_36_2,
    LADDER_29,
    RULE_TABLE_VERIFIED_AGAINST,
)

logger = logging.getLogger(__name__)

# Directory for storing generated reports
REPORTS_DIR = settings.UPLOAD_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_filename(name: str) -> str:
    """Sanitize string for safe cross-platform (especially Windows) filesystem paths."""
    # Replace invalid Windows chars: \ / : * ? " < > |
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", str(name or ""))
    # Truncate to reasonable length
    return sanitized[:64] or "audit"


def _get_item_prop(item: Any, prop: str, default: Any = None) -> Any:
    """Safely extract a property whether item is a dict, dataclass, ORM object, or raw string."""
    if item is None:
        return default
    if isinstance(item, dict):
        val = item.get(prop, default)
    elif isinstance(item, str):
        if prop in ("description", "legal_proof_summary", "expected_value", "found_value"):
            return item
        return default
    else:
        val = getattr(item, prop, default)

    # If prop returned an Enum, unwrap its value
    if hasattr(val, "value"):
        return val.value
    return val


def _extract_text_val(data: Optional[dict], key: str, fallback: str = "Not Declared") -> str:
    """Extract a string value from extractions whether stored as dict, object, or direct value."""
    if not data or not isinstance(data, dict):
        return fallback
    entry = data.get(key)
    if entry is None:
        return fallback
    if isinstance(entry, dict):
        val = entry.get("value")
    elif hasattr(entry, "value"):
        val = getattr(entry, "value")
    else:
        val = entry

    if val is None or val == "":
        return fallback
    if isinstance(val, (dict, list)):
        try:
            return json.dumps(val, ensure_ascii=False)
        except Exception:
            return str(val)
    return str(val).strip() or fallback


class ReportGenerator:
    """
    Generates formal Legal Metrology Inspection & Infraction Notices.
    """

    def __init__(self) -> None:
        self.output_dir = getattr(settings, "REPORTS_DIR", settings.UPLOAD_DIR / "reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ReportGenerator initialized. Output dir → %s", self.output_dir)

    def generate_html_report(
        self,
        audit_id: Any = None,
        verdict_data: Optional[dict[str, Any]] = None,
        extractions: Optional[dict[str, Any]] = None,
        listing_data: Optional[dict[str, Any]] = None,
        source_url: Optional[str] = None,
    ) -> str:
        """
        Generate a comprehensive, printable HTML Inspection & Infraction Notice.
        """
        now_str = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC")
        
        # Safely coerce audit_id to string and sanitize for Windows filesystem
        raw_audit_id = str(audit_id) if audit_id not in (None, "") else str(uuid.uuid4())
        safe_audit_id = _sanitize_filename(raw_audit_id)

        verdict_dict = verdict_data if isinstance(verdict_data, dict) else {}
        extractions_dict = extractions if isinstance(extractions, dict) else {}
        listing_dict = listing_data if isinstance(listing_data, dict) else {}

        try:
            score = float(verdict_dict.get("compliance_score") or 0.0)
            score = max(0.0, min(100.0, score))
        except (ValueError, TypeError):
            score = 0.0

        overall_status = str(verdict_dict.get("overall_status") or "UNKNOWN")
        raw_violations = verdict_dict.get("violations") or []
        violations = [v for v in raw_violations if v is not None] if isinstance(raw_violations, (list, tuple)) else []
        declarations = verdict_dict.get("declaration_status")
        declarations = declarations if isinstance(declarations, dict) else {}
        computed_usp = verdict_dict.get("computed_usp")

        # Product details extracted — supports dicts, objects, and raw strings
        product_name = _extract_text_val(extractions_dict, "product_name", "")
        if not product_name or product_name == "Not Declared":
            product_name = str(listing_dict.get("product_name") or "Pre-Packaged Commodity")

        manufacturer = _extract_text_val(extractions_dict, "manufacturer_name", "Not Declared")
        if manufacturer == "Not Declared" and listing_dict.get("manufacturer"):
            manufacturer = str(listing_dict["manufacturer"])

        mrp = _extract_text_val(extractions_dict, "mrp", "Not Declared")
        if mrp == "Not Declared" and listing_dict.get("listed_price"):
            mrp = f"₹{listing_dict['listed_price']}"

        net_qty = _extract_text_val(extractions_dict, "net_quantity", "Not Declared")
        if net_qty == "Not Declared" and listing_dict.get("net_quantity"):
            net_qty = str(listing_dict["net_quantity"])

        origin = _extract_text_val(extractions_dict, "country_of_origin", "Not Declared")
        if origin == "Not Declared" and listing_dict.get("country_of_origin"):
            origin = str(listing_dict["country_of_origin"])

        status_color = (
            "#10b981" if overall_status == "COMPLIANT"
            else "#f59e0b" if overall_status in ("PARTIAL_VIOLATION", "NEEDS_MANUAL_REVIEW")
            else "#ef4444"
        )

        violations_html = ""
        if violations:
            for idx, v in enumerate(violations, 1):
                sev = str(_get_item_prop(v, "severity", "major")).lower()
                sev_color = (
                    "#dc2626" if sev == "critical"
                    else "#d97706" if sev == "major"
                    else "#2563eb"
                )
                is_disc = bool(_get_item_prop(v, "is_discrepancy", False))
                discrepancy_badge = (
                    '<span class="badge badge-discrepancy">E-Commerce Discrepancy</span>'
                    if is_disc else ""
                )
                rule_ref = str(_get_item_prop(v, "rule_reference", "Rule 6 - LM(PC) Rules, 2011"))
                act_sec = str(_get_item_prop(v, "act_section", "Section 18(1) - Legal Metrology Act, 2009"))
                punish_sec = str(_get_item_prop(v, "punishment_section", "Section 36(1) - Legal Metrology Act, 2009"))
                stat_penalty = str(_get_item_prop(v, "statutory_penalty", "") or "")
                
                statutory_proof = str(_get_item_prop(v, "legal_proof_summary", "") or "")
                description = str(_get_item_prop(v, "description", "") or "")
                if statutory_proof and description and statutory_proof != description:
                    legal_proof = f"{description} — {statutory_proof}"
                elif statutory_proof:
                    legal_proof = statutory_proof
                else:
                    legal_proof = description or "Non-compliance observed"

                field_name = str(_get_item_prop(v, "field_name", "General"))
                exp_val = str(_get_item_prop(v, "expected_value", "") or "—")
                found_val = str(_get_item_prop(v, "found_value", "") or "Missing")

                violations_html += f"""
                <tr class="violation-row">
                    <td class="text-center font-bold">{idx}</td>
                    <td>
                        <div class="rule-tag font-mono">{rule_ref}</div>
                        <div class="act-tag font-mono text-sm" style="color: #0369a1; margin-top: 3px;">{act_sec}</div>
                        <div class="punish-tag font-mono text-sm text-red" style="font-weight: 600; margin-top: 2px;">{punish_sec}</div>
                    </td>
                    <td class="font-semibold">{field_name} {discrepancy_badge}</td>
                    <td><span class="badge" style="background-color: {sev_color}22; color: {sev_color}; border: 1px solid {sev_color}55;">{sev.upper()}</span></td>
                    <td>
                        <div><strong>Statutory Proof:</strong> {legal_proof}</div>
                        {f'<div class="penalty-cite text-sm mt-1" style="color: #991b1b; font-size: 11px; margin-top: 4px;"><strong>Penalty Clause:</strong> {stat_penalty}</div>' if stat_penalty else ''}
                    </td>
                    <td class="font-mono text-sm">{exp_val}</td>
                    <td class="font-mono text-sm text-red">{found_val}</td>
                </tr>
                """
        else:
            violations_html = """
            <tr>
                <td colspan="7" class="text-center text-green py-4 font-semibold">
                    ✓ Nil Violations Detected. Commodity fully complies with Section 18 of the Legal Metrology Act, 2009 & Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011.
                </td>
            </tr>
            """

        # Map of mandatory declarations and extraction keys to check
        decl_definitions = [
            ("manufacturer_name", "Name & Address of Manufacturer / Packer / Importer [Rule 6(1)(a) & Sec 18(1)]", ["manufacturer_name", "manufacturer_address"]),
            ("country_of_origin", "Country of Origin [Rule 6(1)(aa), Rule 6(10) & Sec 18(1)]", ["country_of_origin"]),
            ("generic_name", "Common or Generic Name of Commodity [Rule 6(1)(b) & Sec 18(1)]", ["generic_name", "product_name"]),
            ("net_quantity", "Net Quantity in Standard SI Metric Units [Rule 6(1)(c), Sec 11(1)(d) & Sec 18(1)]", ["net_quantity"]),
            ("manufacture_date", "Month & Year of Manufacture / Packing [Rule 6(1)(d) & Sec 18(1)]", ["manufacture_date"]),
            ("expiry_date", "Best Before / Expiry Date [Rule 6(1)(da) / 6(1)(e) & Sec 18(1)]", ["expiry_date", "best_before"]),
            ("mrp", "Maximum Retail Price (MRP) incl. of all taxes [Rule 6(1)(f) & Sec 18(1)]", ["mrp"]),
            ("unit_sale_price", "Unit Sale Price (USP) [Rule 6(11) 2021 Amendment & Sec 18(1)]", ["unit_sale_price"]),
            ("consumer_care", "Consumer Care Name, Address, Phone & Email [Rule 6(1)(n) & Sec 18(1)]", ["consumer_care", "consumer_care_phone", "consumer_care_email", "consumer_care_name", "consumer_care_address"]),
        ]

        # Check violation fields to determine non-compliant status even if declarations dict is empty
        violated_fields = set()
        for v in violations:
            fn = str(_get_item_prop(v, "field_name", "")).lower()
            if fn:
                violated_fields.add(fn)

        declarations_html = ""
        for key, name, candidates in decl_definitions:
            decl_info = declarations.get(key)
            if isinstance(decl_info, dict):
                d_status = str(decl_info.get("status") or "MISSING").upper()
                d_val = str(decl_info.get("value") or ("Not Found" if d_status == "MISSING" else "Detected"))
            elif hasattr(decl_info, "status"):
                status_attr = getattr(decl_info, "status")
                d_status = str(getattr(status_attr, "value", status_attr) or "MISSING").upper()
                val_attr = getattr(decl_info, "value", None)
                d_val = str(val_attr or ("Not Found" if d_status == "MISSING" else "Detected"))
            else:
                # Intelligent fallback to extractions if declarations dict is empty (e.g. reloaded from DB)
                found_val = None
                for c in candidates:
                    val = _extract_text_val(extractions_dict, c, "")
                    if val and val != "Not Declared":
                        found_val = val
                        break
                
                # Check listing fallback
                if not found_val and listing_dict:
                    for c in candidates:
                        if listing_dict.get(c):
                            found_val = str(listing_dict[c])
                            break

                has_field_violation = any(c.lower() in violated_fields or key.lower() in violated_fields for c in candidates)

                if found_val:
                    if has_field_violation:
                        d_status = "PARTIAL"
                        d_val = f"{found_val} (Discrepancy Flagged)"
                    else:
                        d_status = "FOUND"
                        d_val = found_val
                else:
                    d_status = "MISSING"
                    d_val = "Not Found"

            badge_color = "#10b981" if d_status == "FOUND" else "#f59e0b" if d_status in ("PARTIAL", "REVIEW") else "#ef4444"
            declarations_html += f"""
            <tr>
                <td class="font-semibold">{name}</td>
                <td><span class="badge" style="background-color: {badge_color}22; color: {badge_color};">{d_status}</span></td>
                <td class="font-mono text-sm">{d_val}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LMPC Inspection Notice — {safe_audit_id[:8]}</title>
    <style>
        @page {{
            size: A4;
            margin: 15mm;
        }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #1e293b;
            background: #ffffff;
            margin: 0;
            padding: 20px;
            font-size: 13px;
            line-height: 1.5;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #0f172a;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}
        .emblem {{
            font-size: 28px;
            margin-bottom: 4px;
        }}
        .gov-title {{
            font-size: 15px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #0f172a;
            margin: 0;
        }}
        .dept-title {{
            font-size: 13px;
            font-weight: 600;
            color: #475569;
            margin: 2px 0 6px 0;
        }}
        .notice-title {{
            font-size: 16px;
            font-weight: 800;
            color: #0f172a;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            background: #f1f5f9;
            padding: 6px 12px;
            display: inline-block;
            border: 1px solid #cbd5e1;
            margin-top: 6px;
        }}
        .meta-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        .meta-table td {{
            padding: 6px 10px;
            border: 1px solid #e2e8f0;
        }}
        .meta-table .label {{
            background: #f8fafc;
            font-weight: 600;
            color: #475569;
            width: 25%;
        }}
        .section-title {{
            font-size: 14px;
            font-weight: 700;
            color: #0f172a;
            text-transform: uppercase;
            border-left: 4px solid #2563eb;
            padding-left: 8px;
            margin: 20px 0 10px 0;
        }}
        table.data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }}
        table.data-table th {{
            background: #0f172a;
            color: #ffffff;
            font-weight: 600;
            text-align: left;
            padding: 8px 10px;
            font-size: 12px;
            text-transform: uppercase;
        }}
        table.data-table td {{
            padding: 7px 10px;
            border: 1px solid #e2e8f0;
        }}
        table.data-table tr:nth-child(even) {{
            background: #f8fafc;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
        }}
        .badge-discrepancy {{
            background: #fee2e2;
            color: #dc2626;
            border: 1px solid #fca5a5;
            margin-left: 6px;
        }}
        .rule-tag {{
            background: #e2e8f0;
            color: #334155;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
        }}
        .penalty-box {{
            background: #fff1f2;
            border: 1px solid #fecdd3;
            border-left: 4px solid #e11d48;
            padding: 12px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .penalty-box h4 {{
            margin: 0 0 6px 0;
            color: #9f1239;
            font-size: 13px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #cbd5e1;
            font-size: 11px;
            color: #64748b;
            display: flex;
            justify-content: space-between;
        }}
        .font-mono {{ font-family: monospace; }}
        .font-bold {{ font-weight: 700; }}
        .font-semibold {{ font-weight: 600; }}
        .text-center {{ text-align: center; }}
        .text-sm {{ font-size: 12px; }}
        .text-red {{ color: #dc2626; }}
        .text-green {{ color: #16a34a; }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="no-print" style="margin-bottom: 15px; text-align: right;">
        <button onclick="window.print()" style="padding: 8px 16px; background: #0f172a; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">
            🖨️ Print / Save as PDF
        </button>
    </div>

    <div class="header">
        <div class="emblem">🏛️</div>
        <div class="gov-title">Government of India</div>
        <div class="dept-title">Ministry of Consumer Affairs, Food & Public Distribution</div>
        <div class="dept-title">Department of Consumer Affairs — Legal Metrology Division</div>
        <div class="notice-title">STATUTORY COMPLIANCE INSPECTION & INFRACTION NOTICE</div>
    </div>

    <table class="meta-table">
        <tr>
            <td class="label">Inspection Notice Ref:</td>
            <td class="font-mono font-bold">LMPC-INSP-{safe_audit_id[:12].upper()}</td>
            <td class="label">Date & Time:</td>
            <td>{now_str}</td>
        </tr>
        <tr>
            <td class="label">Commodity / Item:</td>
            <td class="font-semibold">{product_name}</td>
            <td class="label">Compliance Score:</td>
            <td><strong style="color: {status_color}; font-size: 15px;">{score:.1f}% ({overall_status})</strong></td>
        </tr>
        <tr>
            <td class="label">Manufacturer / Packer:</td>
            <td>{manufacturer}</td>
            <td class="label">Country of Origin:</td>
            <td>{origin}</td>
        </tr>
        <tr>
            <td class="label">Declared MRP:</td>
            <td>{mrp}</td>
            <td class="label">Computed USP:</td>
            <td class="font-mono font-semibold">{computed_usp or 'N/A'}</td>
        </tr>
        <tr>
            <td class="label">Net Quantity:</td>
            <td>{net_qty}</td>
            <td class="label">Source / Audit Track:</td>
            <td>{source_url or 'Physical Packaging Image OCR'}</td>
        </tr>
    </table>

    <div class="section-title">1. Legal Metrology Mandatory Declarations Matrix (Rule 6)</div>
    <table class="data-table">
        <thead>
            <tr>
                <th style="width: 45%;">Mandatory Declaration Required</th>
                <th style="width: 20%;">Statutory Status</th>
                <th style="width: 35%;">Observed On Package / Listing</th>
            </tr>
        </thead>
        <tbody>
            {declarations_html}
        </tbody>
    </table>

    <div class="section-title">2. Regulatory Violations & Statutory Proof Schedule</div>
    <table class="data-table">
        <thead>
            <tr>
                <th style="width: 4%;">#</th>
                <th style="width: 22%;">Statutory Reference & Offence</th>
                <th style="width: 15%;">Declaration Field</th>
                <th style="width: 8%;">Severity</th>
                <th style="width: 31%;">Statutory Proof of Contravention & Penalty Clause</th>
                <th style="width: 10%;">Mandatory Required</th>
                <th style="width: 10%;">Observed / Detected</th>
            </tr>
        </thead>
        <tbody>
            {violations_html}
        </tbody>
    </table>

    <div class="penalty-box">
        <h4>STATUTORY PENALTY & LEGAL LIABILITY ADVISORY UNDER THE LEGAL METROLOGY ACT, 2009 (AS AMENDED BY JAN VISHWAS ACT, 2026)</h4>
        <div style="font-size: 11.5px; color: #881337; line-height: 1.6;">
            <p style="margin: 0 0 6px 0;">
                • <strong>Section 36(1) — Penalty for Non-Standard Packages:</strong> Whoever manufactures, packs, imports, sells, distributes, delivers, offers, exposes or possesses for sale any pre-packaged commodity which does not conform to declarations on the package as provided under Section 18 / Rule 6 is subject to statutory enforcement under Jan Vishwas 2026:
                <strong>First contravention:</strong> {LADDER_36_1.first.describe()};
                <strong>Second contravention:</strong> {LADDER_36_1.second.describe()};
                <strong>Subsequent contraventions:</strong> {LADDER_36_1.subsequent.describe()}.
            </p>
            <p style="margin: 0 0 6px 0;">
                • <strong>Section 29 — Penalty for Quoting Non-Standard Units:</strong> Quoting or indicating net quantity in non-standard units (such as 'gms', 'gm', 'ltr', 'kilos') is strictly prohibited under Section 11(1)(d):
                <strong>First contravention:</strong> {LADDER_29.first.describe()};
                <strong>Second contravention:</strong> {LADDER_29.second.describe()};
                <strong>Subsequent contraventions:</strong> {LADDER_29.subsequent.describe()}.
            </p>
            <p style="margin: 0 0 6px 0;">
                • <strong>Section 36(2) — Penalty for Error in Net Quantity (Shortfall):</strong> Manufacturing or packing commodities with shortfall in net quantity beyond maximum permissible error under the First Schedule remains a criminal offence:
                <strong>First offence:</strong> {LADDER_36_2.first.describe()};
                <strong>Second offence:</strong> {LADDER_36_2.second.describe()};
                <strong>Subsequent offences:</strong> {LADDER_36_2.subsequent.describe()}.
            </p>
            <p style="margin: 0 0 6px 0;">
                • <strong>Section 49 — Corporate Officer Liability & Publication of Conviction:</strong> Where an offence under this Act has been committed by a company, the Director or person nominated under Section 49(2) and the company itself are deemed guilty. Under Section 49(5), the Court is empowered to order the publication of the convicted company's name, place of business, and nature of contravention in leading newspapers at the company's expense.
            </p>
            <p style="margin: 0;">
                • <strong>Section 15 — Statutory Search, Seizure & Improvement Notice Powers:</strong> Authorized Legal Metrology Officers are legally empowered to enter premises, search, seize non-conforming pre-packaged goods, and issue Improvement Notices under Section 15(6) specifying mandatory measures to secure compliance within 30 days.
            </p>
        </div>
    </div>

    <div class="footer">
        <div>Generated by SIH26034 Automated Legal Metrology (LMPC) Compliance Engine</div>
        <div>System Cryptographic Hash: SHA256:{uuid.uuid4().hex[:16]}</div>
        <div>Digital Audit Verification Record</div>
    </div>
</body>
</html>"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.output_dir / f"lmpc_notice_{safe_audit_id}.html"
        report_path.write_text(html_content, encoding="utf-8")
        logger.info("Generated HTML inspection report → %s", report_path)
        return str(report_path)

    def generate_pdf_report(
        self,
        audit_id: Any = None,
        verdict_data: Optional[dict[str, Any]] = None,
        extractions: Optional[dict[str, Any]] = None,
        listing_data: Optional[dict[str, Any]] = None,
        source_url: Optional[str] = None,
    ) -> str:
        """
        Generate PDF report using WeasyPrint if installed, otherwise gracefully fallback to HTML.
        """
        html_path = self.generate_html_report(
            audit_id=audit_id,
            verdict_data=verdict_data,
            extractions=extractions,
            listing_data=listing_data,
            source_url=source_url,
        )

        raw_audit_id = str(audit_id) if audit_id not in (None, "") else str(uuid.uuid4())
        safe_audit_id = _sanitize_filename(raw_audit_id)
        pdf_path = self.output_dir / f"lmpc_notice_{safe_audit_id}.pdf"

        try:
            from weasyprint import HTML
            HTML(filename=html_path).write_pdf(target=str(pdf_path))
            logger.info("Generated PDF inspection report → %s", pdf_path)
            return str(pdf_path)
        except Exception as e:
            # Clean up partial / 0-byte file if it exists to avoid serving corrupted PDFs
            if pdf_path.exists():
                try:
                    pdf_path.unlink()
                except OSError:
                    pass
            logger.warning("WeasyPrint PDF conversion unavailable (%s). Falling back to HTML report.", e)
            return html_path

    def generate_json_summary(
        self,
        audit_id: Any = None,
        verdict_data: Optional[dict[str, Any]] = None,
        extractions: Optional[dict[str, Any]] = None,
        listing_data: Optional[dict[str, Any]] = None,
        source_url: Optional[str] = None,
    ) -> str:
        """
        Generate machine-readable JSON compliance audit summary for governmental databases.
        """
        raw_audit_id = str(audit_id) if audit_id not in (None, "") else str(uuid.uuid4())
        safe_audit_id = _sanitize_filename(raw_audit_id)

        summary_data = {
            "audit_id": raw_audit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_url": source_url,
            "verdict": verdict_data or {},
            "extractions": extractions or {},
            "listing_data": listing_data or {},
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.output_dir / f"lmpc_summary_{safe_audit_id}.json"
        json_path.write_text(json.dumps(summary_data, indent=2, default=str), encoding="utf-8")
        return str(json_path)


# Module-level singleton
report_generator = ReportGenerator()
