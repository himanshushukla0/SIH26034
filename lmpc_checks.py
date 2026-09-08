#!/usr/bin/env python3
"""
LMPC COMPLIANCE ENGINE (SIH26034) — STEP 4: CHECK (STATUTORY AUDITOR)
fields → findings

Applies Legal Metrology (Packaged Commodities) Rules, 2011 checks to the
9 Rule 6 fields mapped by Step 3 (lmpc_labelparse.parse_label()):
- Rule 6(1)(a): Manufacturer name and complete address
- Rule 6(1)(a) & Rule 6(10): Country of Origin
- Rule 6(1)(b): Generic or Common Name of commodity
- Rule 6(1)(e): Net Quantity with legal SI units (g, kg, ml, l, no.)
- Rule 6(1)(d): Month and Year of Manufacture / Packing
- Rule 6(1)(d): Expiry date or 'best before' period
- Rule 6(1)(e): Maximum Retail Price with 'inclusive of all taxes'
- Rule 6(1)(h): Unit Sale Price (USP) threshold and arithmetic
- Rule 6(1)(f): Consumer care grievance officer details
"""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    import rule_table
except ImportError:
    from backend import rule_table

from backend.agents.compliance_funnel import (
    DeterministicRuleChecker,
    LEGAL_WEIGHT_UNITS,
    LEGAL_VOLUME_UNITS,
    ILLEGAL_UNIT_ABBREVIATIONS,
)


@dataclass
class Finding:
    clause: str
    rule_id: str
    label: str
    val: str
    status: str  # "PASS" | "FAIL" | "UNVERIFIED"
    severity: str  # "CRITICAL" | "MAJOR" | "MINOR"
    quoted_text: Optional[str] = None
    statutory_action: Optional[str] = None
    detail: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_checks(parsed_fields: Dict[str, Any], has_pin_code: Optional[bool] = None) -> Dict[str, Any]:
    """
    STEP 4: CHECK (fields → findings)
    
    Validates parsed fields against statutory LMPC requirements.
    Returns:
    - findings: list of check objects (PASS/FAIL/UNVERIFIED)
    - passed_count: int
    - failed_count: int
    - overall_status: "COMPLIANT" | "NON_COMPLIANT" | "NEEDS_MANUAL_REVIEW"
    """
    findings: List[Finding] = []
    
    def get_f(key: str) -> Optional[Dict[str, Any]]:
        val = parsed_fields.get(key)
        if val is None:
            return None
        if hasattr(val, "as_dict"):
            return val.as_dict()
        if isinstance(val, dict):
            return val
        return {"value": str(val), "quoted_text": str(val), "confidence": 0.9}

    # 1. MANUFACTURER
    f_mfg = get_f("MANUFACTURER")
    if f_mfg and f_mfg.get("value"):
        findings.append(Finding(
            clause="Rule 6(1)(a)",
            rule_id="MANUFACTURER",
            label="Name & Address of Manufacturer / Packer / Importer",
            val=str(f_mfg["value"]),
            status="PASS",
            severity="MAJOR",
            quoted_text=f_mfg.get("quoted_text"),
        ))
    else:
        findings.append(Finding(
            clause="Rule 6(1)(a)",
            rule_id="MANUFACTURER",
            label="Name & Address of Manufacturer / Packer / Importer",
            val="NOT DECLARED",
            status="FAIL",
            severity="MAJOR",
            detail="Manufacturer name or complete address is missing from the label.",
            statutory_action="Issue Section 15(6) Improvement Notice",
        ))

    # 2. COUNTRY OF ORIGIN
    f_origin = get_f("COUNTRY_OF_ORIGIN")
    if f_origin and f_origin.get("value"):
        findings.append(Finding(
            clause="Rule 6(1)(a)",
            rule_id="COUNTRY_OF_ORIGIN",
            label="Country of Origin",
            val=str(f_origin["value"]),
            status="PASS",
            severity="MAJOR",
            quoted_text=f_origin.get("quoted_text"),
        ))
    else:
        findings.append(Finding(
            clause="Rule 6(1)(a)",
            rule_id="COUNTRY_OF_ORIGIN",
            label="Country of Origin",
            val="NOT DECLARED",
            status="FAIL",
            severity="MAJOR",
            detail="Country of Origin declaration is mandatory for all commodities.",
            statutory_action="Issue Section 15(6) Improvement Notice",
        ))

    # 3. GENERIC NAME (Deliberately unparsed by regex — requires vision model or officer confirmation)
    f_name = get_f("GENERIC_NAME")
    if f_name and f_name.get("value"):
        findings.append(Finding(
            clause="Rule 6(1)(b)",
            rule_id="GENERIC_NAME",
            label="Generic or Common Name of Commodity",
            val=str(f_name["value"]),
            status="PASS",
            severity="MAJOR",
            quoted_text=f_name.get("quoted_text"),
        ))
    else:
        findings.append(Finding(
            clause="Rule 6(1)(b)",
            rule_id="GENERIC_NAME",
            label="Generic or Common Name of Commodity",
            val="UNVERIFIED (Descriptive line unparsed by regex — requires vision model or officer confirmation)",
            status="UNVERIFIED",
            severity="MAJOR",
            detail="GENERIC_NAME has no conventional keyword anchor; left unparsed by regex to prevent hallucination.",
        ))

    # 4. NET QUANTITY & LEGAL UNITS
    f_qty = get_f("NET_QUANTITY")
    if f_qty and f_qty.get("value"):
        unit = f_qty.get("normalized_unit") or ""
        # Check legal SI units
        ok_unit, err_unit = DeterministicRuleChecker.check_si_units(unit) if unit else (True, None)
        if not ok_unit and err_unit:
            findings.append(Finding(
                clause="Rule 6(1)(e)",
                rule_id="NET_QUANTITY",
                label="Net Quantity & Legal SI Units",
                val=str(f_qty["value"]),
                status="FAIL",
                severity="MAJOR",
                quoted_text=f_qty.get("quoted_text"),
                detail=err_unit,
                statutory_action="Notice under Section 11 read with Section 29 (Non-standard units)",
            ))
        else:
            findings.append(Finding(
                clause="Rule 6(1)(e)",
                rule_id="NET_QUANTITY",
                label="Net Quantity & Legal SI Units",
                val=str(f_qty["value"]),
                status="PASS",
                severity="CRITICAL",
                quoted_text=f_qty.get("quoted_text"),
            ))
    else:
        findings.append(Finding(
            clause="Rule 6(1)(e)",
            rule_id="NET_QUANTITY",
            label="Net Quantity & Legal SI Units",
            val="NOT DECLARED",
            status="FAIL",
            severity="CRITICAL",
            detail="Net Quantity declaration is completely missing.",
            statutory_action="Issue Section 15(6) Improvement Notice",
        ))

    # 5. DATE OF MANUFACTURE
    f_mfg_dt = get_f("DATE_OF_MANUFACTURE")
    if f_mfg_dt and f_mfg_dt.get("value"):
        findings.append(Finding(
            clause="Rule 6(1)(d)",
            rule_id="DATE_OF_MANUFACTURE",
            label="Month & Year of Manufacture / Packing",
            val=str(f_mfg_dt["value"]),
            status="PASS",
            severity="MAJOR",
            quoted_text=f_mfg_dt.get("quoted_text"),
        ))
    else:
        findings.append(Finding(
            clause="Rule 6(1)(d)",
            rule_id="DATE_OF_MANUFACTURE",
            label="Month & Year of Manufacture / Packing",
            val="NOT DECLARED",
            status="FAIL",
            severity="MAJOR",
            detail="Month and Year of manufacture or packing is missing.",
        ))

    # 6. BEST BEFORE / EXPIRY
    f_exp = get_f("BEST_BEFORE")
    if f_exp and f_exp.get("value"):
        findings.append(Finding(
            clause="Rule 6(1)(d)",
            rule_id="BEST_BEFORE",
            label="Best Before or Expiry Date",
            val=str(f_exp["value"]),
            status="PASS",
            severity="MAJOR",
            quoted_text=f_exp.get("quoted_text"),
        ))
    else:
        findings.append(Finding(
            clause="Rule 6(1)(d)",
            rule_id="BEST_BEFORE",
            label="Best Before or Expiry Date",
            val="NOT DECLARED",
            status="FAIL",
            severity="MAJOR",
            detail="Expiry or Best Before declaration is missing.",
        ))

    # 7. MAXIMUM RETAIL PRICE (MRP)
    f_mrp = get_f("MRP")
    if f_mrp and f_mrp.get("value"):
        quoted_mrp = f_mrp.get("quoted_text") or ""
        ok_tax, err_tax = DeterministicRuleChecker.check_mrp_format(quoted_mrp)
        if not ok_tax and err_tax:
            findings.append(Finding(
                clause="Rule 6(1)(e)",
                rule_id="MRP",
                label="Maximum Retail Price (MRP) & Tax Inclusion",
                val=str(f_mrp["value"]),
                status="FAIL",
                severity="MAJOR",
                quoted_text=quoted_mrp,
                detail=err_tax,
                statutory_action="Issue Section 15(6) Improvement Notice",
            ))
        else:
            findings.append(Finding(
                clause="Rule 6(1)(e)",
                rule_id="MRP",
                label="Maximum Retail Price (MRP) & Tax Inclusion",
                val=str(f_mrp["value"]),
                status="PASS",
                severity="CRITICAL",
                quoted_text=quoted_mrp,
            ))
    else:
        findings.append(Finding(
            clause="Rule 6(1)(e)",
            rule_id="MRP",
            label="Maximum Retail Price (MRP) & Tax Inclusion",
            val="NOT DECLARED",
            status="FAIL",
            severity="CRITICAL",
            detail="Maximum Retail Price (MRP) is completely missing.",
            statutory_action="Issue Section 15(6) Improvement Notice",
        ))

    # 8. UNIT SALE PRICE (USP)
    f_usp = get_f("UNIT_SALE_PRICE")
    mrp_num = f_mrp.get("normalized_numeric") if f_mrp else None
    qty_num = f_qty.get("normalized_numeric") if f_qty else None
    qty_unit = f_qty.get("normalized_unit") if f_qty else None
    usp_num = f_usp.get("normalized_numeric") if f_usp else None
    usp_unit = f_usp.get("normalized_unit") if f_usp else None

    ok_usp, err_usp = DeterministicRuleChecker.check_unit_sale_price(
        mrp_val=mrp_num,
        net_quantity_val=qty_num,
        net_quantity_unit=qty_unit,
        declared_usp_val=usp_num,
        declared_usp_unit=usp_unit,
    )
    if not ok_usp and err_usp:
        findings.append(Finding(
            clause="Rule 6(1)(h)",
            rule_id="UNIT_SALE_PRICE",
            label="Unit Sale Price (USP)",
            val=str(f_usp.get("value") if f_usp else "NOT DECLARED"),
            status="FAIL",
            severity="CRITICAL",
            quoted_text=f_usp.get("quoted_text") if f_usp else None,
            detail=err_usp,
            statutory_action="Issue Section 15(6) Improvement Notice (Mandatory USP)",
        ))
    else:
        findings.append(Finding(
            clause="Rule 6(1)(h)",
            rule_id="UNIT_SALE_PRICE",
            label="Unit Sale Price (USP)",
            val=str(f_usp.get("value") if (f_usp and f_usp.get("value")) else "Compliant (Below 1kg/1L threshold)"),
            status="PASS",
            severity="MAJOR",
            quoted_text=f_usp.get("quoted_text") if f_usp else None,
        ))

    # 9. CONSUMER CARE
    f_care = get_f("CONSUMER_CARE")
    if f_care and f_care.get("value"):
        findings.append(Finding(
            clause="Rule 6(1)(f)",
            rule_id="CONSUMER_CARE",
            label="Consumer Care Grievance Details",
            val=str(f_care["value"]),
            status="PASS",
            severity="MAJOR",
            quoted_text=f_care.get("quoted_text"),
        ))
    else:
        findings.append(Finding(
            clause="Rule 6(1)(f)",
            rule_id="CONSUMER_CARE",
            label="Consumer Care Grievance Details",
            val="NOT DECLARED",
            status="FAIL",
            severity="MAJOR",
            detail="Consumer care email address or telephone number is missing.",
            statutory_action="Issue Section 15(6) Improvement Notice",
        ))

    # Check label-wide 6-digit PIN code absence
    if has_pin_code is False:
        findings.append(Finding(
            clause="Rule 6(1)(a)",
            rule_id="PIN_CODE_ABSENCE",
            label="Mandatory 6-Digit Indian Postal PIN Code",
            val="NOT FOUND ACROSS LABEL",
            status="FAIL",
            severity="MAJOR",
            detail="Rule 6(1)(a) Absence Finding: No 6-digit Indian PIN code was detected anywhere on the packaging label.",
            statutory_action="Issue Section 15(6) Improvement Notice",
        ))

    passed = sum(1 for f in findings if f.status == "PASS")
    failed = sum(1 for f in findings if f.status == "FAIL")
    unverified = sum(1 for f in findings if f.status == "UNVERIFIED")

    if failed > 0:
        overall = "NON_COMPLIANT"
    elif unverified > 0:
        overall = "INSUFFICIENT_DATA"
    else:
        overall = "COMPLIANT"

    return {
        "findings": [f.as_dict() for f in findings],
        "passed": passed,
        "failed": failed,
        "unverified": unverified,
        "total": len(findings),
        "overall_status": overall,
        "compliance_score_percent": round((passed / len(findings)) * 100.0, 1),
    }
