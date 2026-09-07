"""
SIH26034 — Agent 3: LMPC Legal & Regulatory Auditor Agent

Implements the full Legal Metrology (Packaged Commodities) Rules, 2011
compliance checking engine. Validates all 10 mandatory declarations,
computes Unit Sale Price (USP), checks font/unit formatting, and detects
cross-modal discrepancies between physical packaging and e-commerce listings.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Legal constants
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Statutory Legal Constants (Legal Metrology Act, 2009 & LM(PC) Rules, 2011)
# Enacted by Ministry of Consumer Affairs, Food & Public Distribution, India
# ---------------------------------------------------------------------------

ACT_NAME = "The Legal Metrology Act, 2009 (Act No. 1 of 2010)"
RULES_NAME = "Legal Metrology (Packaged Commodities) Rules, 2011"
MINISTRY_AUTHORITY = (
    "Ministry of Consumer Affairs, Food & Public Distribution "
    "(Department of Consumer Affairs), Government of India"
)

from backend.rule_table import (
    rule,
    consequence_for,
    max_permissible_error,
    IMPROVEMENT_NOTICE,
    CIVIL_PENALTY,
    CRIMINAL_FINE,
    LADDER_36_1,
    LADDER_36_2,
    LADDER_29,
)

# Standard statutory penalty clauses under the Act (Incorporating Jan Vishwas Act, 2026, in force 01-05-2026)
PENALTY_SEC_36_1 = (
    f"Section 36(1), Legal Metrology Act, 2009 (Jan Vishwas 2026 regime): "
    f"First contravention: {LADDER_36_1.first.describe()} "
    f"Second contravention: {LADDER_36_1.second.describe()}. "
    f"Subsequent contravention: {LADDER_36_1.subsequent.describe()}."
)

PENALTY_SEC_29 = (
    f"Section 29, Legal Metrology Act, 2009 (Jan Vishwas 2026 regime): "
    f"First contravention: {LADDER_29.first.describe()} "
    f"Second contravention: {LADDER_29.second.describe()}. "
    f"Subsequent contravention: {LADDER_29.subsequent.describe()}."
)

PENALTY_SEC_36_2 = (
    f"Section 36(2), Legal Metrology Act, 2009: "
    f"First contravention: {LADDER_36_2.first.describe()}. "
    f"Second contravention: {LADDER_36_2.second.describe()}. "
    f"Subsequent contravention: {LADDER_36_2.subsequent.describe()}."
)

CORPORATE_LIABILITY_NOTICE = (
    "Section 49 of Legal Metrology Act, 2009: In case of company contraventions, the company "
    "and its Director / Nominated Person under Section 49(2) are legally liable. "
    "Under Section 49(5), the Court is empowered to publish the company's conviction in newspapers at company expense."
)

INSPECTION_SEIZURE_AUTHORITY = (
    "Section 15 of Legal Metrology Act, 2009 empowers authorized Legal Metrology Officers "
    "to search premises and seize non-conforming pre-packaged commodities."
)

# Rule 7 & Rule 23 Table 1: PDP Area → Minimum Font Height (mm)
PDP_FONT_THRESHOLDS: list[tuple[float, float, float]] = [
    # (max_area_cm2, min_height_general_mm, min_height_blown_mm)
    (50.0, 1.0, 1.5),
    (100.0, 1.5, 3.0),
    (500.0, 2.0, 4.0),
    (2500.0, 4.0, 6.0),
    (float("inf"), 6.0, 6.0),
]

# Legal SI units accepted under LMPC Rules
LEGAL_WEIGHT_UNITS = {"g", "kg"}
LEGAL_VOLUME_UNITS = {"ml", "l", "L"}
LEGAL_LENGTH_UNITS = {"cm", "m", "mm"}
LEGAL_COUNT_UNITS = {"N", "units", "unit", "nos", "pieces", "pcs"}

# Common illegal/non-standard unit abbreviations
ILLEGAL_UNIT_MAP: dict[str, str] = {
    "gms": "g",
    "gm": "g",
    "grm": "g",
    "gram": "g",
    "grams": "g",
    "kilos": "kg",
    "kgs": "kg",
    "ltr": "l",
    "ltrs": "l",
    "litre": "l",
    "litres": "l",
    "liter": "l",
    "liters": "l",
    "mls": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
}


@dataclass
class ViolationRecord:
    """A single regulatory violation detected during audit with statutory citations."""
    rule_reference: str
    field_name: str
    severity: str  # "critical", "major", "minor"
    description: str
    expected_value: Optional[str] = None
    found_value: Optional[str] = None
    is_discrepancy: bool = False
    act_section: str = "Section 18(1) - Legal Metrology Act, 2009"
    punishment_section: str = "Section 36(1) - Legal Metrology Act, 2009"
    statutory_penalty: str = PENALTY_SEC_36_1
    legal_proof_summary: str = ""


@dataclass
class AuditVerdict:
    """Final compliance audit result backed by Ministry of Consumer Affairs statutes."""
    compliance_score: float  # 0.0 — 100.0
    total_checks: int
    passed_checks: int
    failed_checks: int
    overall_status: str  # "COMPLIANT", "NON_COMPLIANT", "PARTIAL_VIOLATION", "NEEDS_MANUAL_REVIEW"
    violations: list[ViolationRecord] = field(default_factory=list)
    declaration_status: dict[str, dict] = field(default_factory=dict)
    computed_usp: Optional[str] = None
    statutory_authority: str = MINISTRY_AUTHORITY
    governing_act: str = ACT_NAME
    governing_rules: str = RULES_NAME
    corporate_liability_clause: str = CORPORATE_LIABILITY_NOTICE
    manual_review_reasons: list[str] = field(default_factory=list)


class LMPCEvaluator:
    """
    Legal Metrology (Packaged Commodities) Rules, 2011 compliance evaluator.

    Checks all 10 mandatory declarations from Rule 6, validates unit formats,
    computes Unit Sale Price (USP), and detects cross-modal discrepancies
    when e-commerce listing data is provided.
    """

    # Weights for compliance score calculation
    FIELD_WEIGHTS: dict[str, float] = {
        "manufacturer_name": 10.0,
        "manufacturer_address": 5.0,
        "country_of_origin": 10.0,
        "generic_name": 8.0,
        "net_quantity": 12.0,
        "manufacture_date": 8.0,
        "expiry_date": 10.0,
        "mrp": 15.0,
        "unit_sale_price": 12.0,
        "consumer_care": 10.0,
    }

    def evaluate(
        self,
        extractions: dict[str, Any],
        listing_data: Optional[dict[str, Any]] = None,
    ) -> AuditVerdict:
        """
        Run the full LMPC compliance evaluation.

        Args:
            extractions: Output from VisionAgent.extract_from_image().
            listing_data: Optional e-commerce listing data from ScraperAgent.

        Returns:
            AuditVerdict with score, violations, and per-declaration status.
        """
        violations: list[ViolationRecord] = []
        declaration_status: dict[str, dict] = {}
        total_weight = sum(self.FIELD_WEIGHTS.values())
        earned_weight = 0.0

        # ----- Check 1: Manufacturer / Packer / Importer (Rule 6(1)(a)) -----
        mfg_name = self._get_value(extractions, "manufacturer_name")
        mfg_addr = self._get_value(extractions, "manufacturer_address")

        if mfg_name:
            declaration_status["manufacturer_name"] = {
                "status": "FOUND", "value": mfg_name
            }
            earned_weight += self.FIELD_WEIGHTS["manufacturer_name"]
        else:
            declaration_status["manufacturer_name"] = {"status": "MISSING"}
            violations.append(ViolationRecord(
                rule_reference=rule("MANUFACTURER").citation,
                act_section=rule("MANUFACTURER").obligation_section,
                punishment_section=rule("MANUFACTURER").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Manufacturer / Packer Name",
                severity="critical",
                description="Name of manufacturer, packer, or importer is not declared on the package.",
                expected_value="Full legal corporate / business name of manufacturer or packer",
                found_value="Missing / Not Declared",
                legal_proof_summary=(
                    "Section 18(1) of Legal Metrology Act, 2009 mandates that no person shall "
                    "manufacture, pack, sell, or distribute any pre-packaged commodity unless it bears "
                    "prescribed declarations under Rule 6(1)(a). Missing manufacturer identity is a "
                    "statutory offence punishable under Section 36(1)."
                ),
            ))

        if mfg_addr:
            declaration_status["manufacturer_address"] = {
                "status": "FOUND", "value": mfg_addr
            }
            earned_weight += self.FIELD_WEIGHTS["manufacturer_address"]
        else:
            declaration_status["manufacturer_address"] = {"status": "MISSING"}
            violations.append(ViolationRecord(
                rule_reference=rule("MANUFACTURER").citation,
                act_section=rule("MANUFACTURER").obligation_section,
                punishment_section=rule("MANUFACTURER").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Manufacturer / Packer Address",
                severity="major",
                description="Complete geographical address of manufacturer/packer/importer is missing.",
                expected_value="Complete address including premises, locality, city, state and PIN code",
                found_value="Missing / Incomplete",
                legal_proof_summary=(
                    "Under Rule 6(1)(a) of LM(PC) Rules, 2011 enforced under Section 18(1), "
                    "pre-packaged goods must declare the complete address to enable consumer "
                    "redressal and territorial jurisdiction of Legal Metrology Officers under Section 15."
                ),
            ))

        # ----- Check 2: Country of Origin (Rule 6(1)(aa)) -----
        country = self._get_value(extractions, "country_of_origin")
        is_imported = self._get_value(extractions, "is_imported")

        if country:
            declaration_status["country_of_origin"] = {
                "status": "FOUND", "value": country
            }
            earned_weight += self.FIELD_WEIGHTS["country_of_origin"]
        else:
            severity = "critical" if is_imported else "major"
            declaration_status["country_of_origin"] = {"status": "MISSING"}
            violations.append(ViolationRecord(
                rule_reference=rule("COUNTRY_OF_ORIGIN").citation,
                act_section=rule("COUNTRY_OF_ORIGIN").obligation_section,
                punishment_section=rule("COUNTRY_OF_ORIGIN").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Country of Origin",
                severity=severity,
                description=(
                    "Country of Origin is not declared. Mandatory for ALL imported products, "
                    "domestic pre-packaged commodities, and digital e-commerce marketplace listings."
                ),
                expected_value="Country of Origin (e.g., 'Made in India', 'Country of Origin: India')",
                found_value="Missing",
                legal_proof_summary=(
                    "Contravening Section 18(1) of the Legal Metrology Act, 2009 read with Rule 6(1)(aa) "
                    "and Rule 6(10) of the LM(PC) Rules, 2011 and Ministry of Consumer Affairs Advisory No. WM-10(28)/2020."
                ),
            ))

        # ----- Check 3: Generic / Common Name (Rule 6(1)(b)) -----
        generic = self._get_value(extractions, "generic_name")
        if generic:
            declaration_status["generic_name"] = {
                "status": "FOUND", "value": generic
            }
            earned_weight += self.FIELD_WEIGHTS["generic_name"]
        else:
            declaration_status["generic_name"] = {"status": "MISSING"}
            violations.append(ViolationRecord(
                rule_reference=rule("GENERIC_NAME").citation,
                act_section=rule("GENERIC_NAME").obligation_section,
                punishment_section=rule("GENERIC_NAME").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Common / Generic Name",
                severity="minor",
                description="Common or generic name of the commodity is not declared on the package.",
                expected_value="Standard common or generic name of the commodity",
                found_value="Missing",
                legal_proof_summary=(
                    "Contravening Section 18(1) of the Legal Metrology Act, 2009 read with Rule 6(1)(b) "
                    "of the LM(PC) Rules, 2011. Commercial brand names cannot substitute statutory generic naming."
                ),
            ))

        # ----- Check 4: Net Quantity (Rule 6(1)(c) & Section 11(1)(d)) -----
        net_qty = self._get_value(extractions, "net_quantity")
        net_unit = self._get_value(extractions, "net_quantity_unit")
        net_value = self._get_value(extractions, "net_quantity_value")

        if net_qty and net_value:
            declaration_status["net_quantity"] = {
                "status": "FOUND",
                "value": net_qty,
                "unit": net_unit,
                "numeric_value": net_value,
            }
            # Validate unit format
            unit_violation = self._validate_unit(net_unit)
            if unit_violation:
                violations.append(unit_violation)
                earned_weight += self.FIELD_WEIGHTS["net_quantity"] * 0.5
            else:
                earned_weight += self.FIELD_WEIGHTS["net_quantity"]
        else:
            declaration_status["net_quantity"] = {"status": "MISSING"}
            violations.append(ViolationRecord(
                rule_reference=rule("NET_QUANTITY").citation,
                act_section=rule("NET_QUANTITY").obligation_section,
                punishment_section=rule("NET_QUANTITY").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Net Quantity",
                severity="critical",
                description="Net quantity declaration is missing from the package.",
                expected_value="Net quantity in standard metric units (g, kg, ml, l, cm, m, units)",
                found_value="Missing",
                legal_proof_summary=(
                    "Contravening Section 18(1) and Section 11(1)(d) of the Legal Metrology Act, 2009 read with "
                    "Rule 6(1)(c) of the LM(PC) Rules, 2011. Net quantity must be explicitly declared on the Principal Display Panel."
                ),
            ))

        # ----- Check 5: Month & Year of Mfg/Packing (Rule 6(1)(d)) -----
        mfg_date = self._get_value(extractions, "manufacture_date")
        if mfg_date:
            declaration_status["manufacture_date"] = {
                "status": "FOUND", "value": mfg_date
            }
            earned_weight += self.FIELD_WEIGHTS["manufacture_date"]
        else:
            declaration_status["manufacture_date"] = {"status": "MISSING"}
            violations.append(ViolationRecord(
                rule_reference=rule("DATE_OF_MANUFACTURE").citation,
                act_section=rule("DATE_OF_MANUFACTURE").obligation_section,
                punishment_section=rule("DATE_OF_MANUFACTURE").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Month & Year of Manufacture/Packing",
                severity="major",
                description="Month and year of manufacture or pre-packing or import is not declared.",
                expected_value="MM/YYYY or Month Year",
                found_value="Missing",
                legal_proof_summary=(
                    "Contravening Section 18(1) of the Legal Metrology Act, 2009 read with Rule 6(1)(d) "
                    "of the LM(PC) Rules, 2011. Pre-packaged commodities must state month and year of packing/import."
                ),
            ))

        # ----- Check 6: Best Before / Expiry Date (Rule 6(1)(da)) -----
        expiry = self._get_value(extractions, "expiry_date")
        best_before = self._get_value(extractions, "best_before")
        expiry_found = expiry or best_before

        if expiry_found:
            declaration_status["expiry_date"] = {
                "status": "FOUND", "value": expiry_found
            }
            earned_weight += self.FIELD_WEIGHTS["expiry_date"]
        else:
            declaration_status["expiry_date"] = {"status": "MISSING"}
            violations.append(ViolationRecord(
                rule_reference=rule("BEST_BEFORE").citation,
                act_section=rule("BEST_BEFORE").obligation_section,
                punishment_section=rule("BEST_BEFORE").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Best Before / Expiry Date",
                severity="critical",
                description=(
                    "Best Before or Expiry date is not declared. Mandatory for food, cosmetics, "
                    "pharmaceuticals, and perishable commodities."
                ),
                expected_value="Best Before / Expiry date (MM/YYYY or 'Best before X months from packaging')",
                found_value="Missing",
                legal_proof_summary=(
                    "Contravening Section 18(1) of the Legal Metrology Act, 2009 read with Rule 6(1)(da) "
                    "of the LM(PC) Rules, 2011 for perishable, food, and cosmetic commodities."
                ),
            ))

        # ----- Check 7: MRP (Rule 6(1)(e)) -----
        mrp_str = self._get_value(extractions, "mrp")
        mrp_incl_tax = self._get_value(extractions, "mrp_includes_taxes")

        if mrp_str:
            declaration_status["mrp"] = {
                "status": "FOUND",
                "value": mrp_str,
                "includes_taxes": mrp_incl_tax,
            }
            earned_weight += self.FIELD_WEIGHTS["mrp"]

            if mrp_incl_tax is False:
                violations.append(ViolationRecord(
                    rule_reference=rule("MRP").citation,
                    act_section="Section 11(1)(a) & Section 18(1) - Legal Metrology Act, 2009",
                    punishment_section=rule("MRP").ladder.section,
                    statutory_penalty=PENALTY_SEC_36_1,
                    field_name="MRP Tax Clause",
                    severity="minor",
                    description="MRP must be declared as 'inclusive of all taxes'.",
                    expected_value="MRP ₹XX (inclusive of all taxes) or 'incl. of all taxes'",
                    found_value=f"₹{mrp_str} without tax clause",
                    legal_proof_summary=(
                        "Rule 6(1)(e) explicitly mandates that retail sale price must state 'inclusive of all taxes' "
                        "to protect consumers from unstated tax markups at point of sale."
                    ),
                ))
        else:
            declaration_status["mrp"] = {"status": "MISSING"}
            violations.append(ViolationRecord(
                rule_reference=rule("MRP").citation,
                act_section=rule("MRP").obligation_section,
                punishment_section=rule("MRP").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Maximum Retail Price (MRP)",
                severity="critical",
                description="Maximum Retail Price (MRP) is not declared on the package.",
                expected_value="MRP ₹XX (inclusive of all taxes)",
                found_value="Missing",
                legal_proof_summary=(
                    "Contravening Section 18(1) of the Legal Metrology Act, 2009 read with Rule 6(1)(e) "
                    "of the LM(PC) Rules, 2011. Pre-packaged commodities sold without declared retail sale price "
                    "are illegal non-standard packages under Section 36(1)."
                ),
            ))

        # ----- Check 8: Unit Sale Price (Rule 6(11)) -----
        usp_str = self._get_value(extractions, "unit_sale_price")
        computed_usp = self._compute_usp(mrp_str, net_value, net_unit)

        if usp_str:
            declaration_status["unit_sale_price"] = {
                "status": "FOUND",
                "value": usp_str,
                "computed": computed_usp,
            }
            earned_weight += self.FIELD_WEIGHTS["unit_sale_price"]
        else:
            declaration_status["unit_sale_price"] = {
                "status": "MISSING",
                "computed": computed_usp,
            }
            violations.append(ViolationRecord(
                rule_reference=rule("UNIT_SALE_PRICE").citation,
                act_section=rule("UNIT_SALE_PRICE").obligation_section,
                punishment_section=rule("UNIT_SALE_PRICE").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Unit Sale Price (USP)",
                severity="major",
                description=(
                    "Unit Sale Price is not declared. Mandatory under Rule 6(11) "
                    "(inserted by G.S.R. 779(E)) for all pre-packaged commodities."
                ),
                expected_value=computed_usp or "₹X.XX per g/ml/kg/l/unit",
                found_value="Missing",
                legal_proof_summary=(
                    "Contravening Rule 6(11) of the LM(PC) Rules, 2011 inserted by the Ministry of Consumer Affairs "
                    "Notification G.S.R. 779(E) dated 2nd November 2021, and enforceable under Section 18(1) of the Legal Metrology Act, 2009."
                ),
            ))

        # ----- Check 9: Consumer Care Details (Rule 6(1)(n)) -----
        care_name = self._get_value(extractions, "consumer_care_name")
        care_phone = self._get_value(extractions, "consumer_care_phone")
        care_email = self._get_value(extractions, "consumer_care_email")
        care_found = any([care_name, care_phone, care_email])

        if care_found:
            declaration_status["consumer_care"] = {
                "status": "FOUND" if all([care_name, care_phone, care_email]) else "PARTIAL",
                "name": care_name,
                "phone": care_phone,
                "email": care_email,
            }
            if all([care_name, care_phone, care_email]):
                earned_weight += self.FIELD_WEIGHTS["consumer_care"]
            else:
                earned_weight += self.FIELD_WEIGHTS["consumer_care"] * 0.5
                missing_parts = []
                if not care_name:
                    missing_parts.append("name/designation")
                if not care_phone:
                    missing_parts.append("phone number")
                if not care_email:
                    missing_parts.append("email address")
                violations.append(ViolationRecord(
                    rule_reference=rule("CONSUMER_CARE").citation,
                    act_section=rule("CONSUMER_CARE").obligation_section,
                    punishment_section=rule("CONSUMER_CARE").ladder.section,
                    statutory_penalty=PENALTY_SEC_36_1,
                    field_name="Consumer Care Details",
                    severity="major",
                    description=f"Consumer care details incomplete. Missing statutory element(s): {', '.join(missing_parts)}.",
                    expected_value="Name, complete address, phone number, and email ID",
                    found_value="Partially provided",
                    legal_proof_summary=(
                        "Rule 6(1)(n) requires all four consumer grievance elements: contact person/office, "
                        "postal address, telephone number, and email address."
                    ),
                ))
        else:
            declaration_status["consumer_care"] = {"status": "MISSING"}
            violations.append(ViolationRecord(
                rule_reference=rule("CONSUMER_CARE").citation,
                act_section=rule("CONSUMER_CARE").obligation_section,
                punishment_section=rule("CONSUMER_CARE").ladder.section,
                statutory_penalty=PENALTY_SEC_36_1,
                field_name="Consumer Care / Grievance Details",
                severity="major",
                description="Consumer care contact details (name/designation, address, phone, email) are completely missing.",
                expected_value="Name, Address, Phone number, and Email ID of grievance contact",
                found_value="Missing",
                legal_proof_summary=(
                    "Contravening Section 18(1) of the Legal Metrology Act, 2009 read with Rule 6(1)(n) "
                    "of the LM(PC) Rules, 2011. Every pre-packaged commodity must provide consumer redressal channels."
                ),
            ))

        # ----- Check 10: Principal Display Panel (PDP) Font Height (Rule 7 & 23) -----
        pdp_area = extractions.get("pdp_area_cm2")
        font_height = extractions.get("detected_font_height_mm")
        if pdp_area and font_height:
            try:
                area_val = float(pdp_area)
                font_val = float(font_height)
                req_h = self._get_required_font_height(area_val)
                if font_val < req_h:
                    violations.append(ViolationRecord(
                        rule_reference="Rule 7 & Rule 23 Table 1 - LM(PC) Rules, 2011",
                        act_section="Section 18(1) - Legal Metrology Act, 2009",
                        punishment_section="Section 36(1) - Legal Metrology Act, 2009",
                        statutory_penalty=PENALTY_SEC_36_1,
                        field_name="Principal Display Panel (PDP) Font Height",
                        severity="minor",
                        description=(
                            f"Numeral/letter font height ({font_val} mm) is below the statutory minimum "
                            f"({req_h} mm) for PDP area {area_val} sq.cm."
                        ),
                        expected_value=f"≥ {req_h} mm",
                        found_value=f"{font_val} mm",
                        legal_proof_summary=(
                            f"Under Rule 23 Table 1 of LM(PC) Rules, 2011 enforced under Section 18(1), "
                            f"the minimum height for numerals and letters on a PDP of area {area_val} cm² is {req_h} mm."
                        ),
                    ))
            except (ValueError, TypeError):
                pass

        # ----- Check 11: Cross-Modal E-Commerce Discrepancies -----
        if listing_data:
            discrepancy_violations = self._check_cross_modal_discrepancies(
                extractions, listing_data
            )
            violations.extend(discrepancy_violations)

        # ----- Compute Final Score & Three-Tier Verdict -----
        compliance_score = round((earned_weight / total_weight) * 100, 1)
        passed = sum(
            1 for d in declaration_status.values()
            if d.get("status") == "FOUND"
        )
        failed = sum(
            1 for d in declaration_status.values()
            if d.get("status") == "MISSING"
        )

        # Confidence & readability analysis to prevent wrongful flat pass/fail
        readability = extractions.get("label_readability", "clear")
        manual_review_reasons: list[str] = []

        if isinstance(readability, str) and readability.lower() in {"blurry", "damaged", "partially_obscured"}:
            manual_review_reasons.append(
                f"Packaging label readability is classified as '{readability}'. "
                f"Physical inspection recommended under Section 15 of Legal Metrology Act, 2009 before formal summons."
            )

        # Check confidence of detected non-null fields
        found_confidences = []
        for k, v in extractions.items():
            if isinstance(v, dict) and v.get("value") is not None and "confidence" in v:
                try:
                    found_confidences.append(float(v["confidence"]))
                except (ValueError, TypeError):
                    pass

        if found_confidences:
            avg_conf = sum(found_confidences) / len(found_confidences)
            if avg_conf < 0.65:
                manual_review_reasons.append(
                    f"Average OCR extraction confidence ({avg_conf:.2f}) is below standard statutory threshold (0.65). "
                    f"Requires manual verification by a Legal Metrology Officer under Section 15."
                )

        if manual_review_reasons:
            overall_status = "NEEDS_MANUAL_REVIEW"
        elif compliance_score >= 90:
            overall_status = "COMPLIANT"
        elif compliance_score >= 50:
            overall_status = "PARTIAL_VIOLATION"
        else:
            overall_status = "NON_COMPLIANT"

        verdict = AuditVerdict(
            compliance_score=compliance_score,
            total_checks=len(declaration_status),
            passed_checks=passed,
            failed_checks=failed,
            overall_status=overall_status,
            violations=violations,
            declaration_status=declaration_status,
            computed_usp=computed_usp,
            statutory_authority=MINISTRY_AUTHORITY,
            governing_act=ACT_NAME,
            governing_rules=RULES_NAME,
            corporate_liability_clause=CORPORATE_LIABILITY_NOTICE,
            manual_review_reasons=manual_review_reasons,
        )

        logger.info(
            "LMPC Audit complete: %.1f%% (%s) — %d violations found.",
            compliance_score,
            overall_status,
            len(violations),
        )
        return verdict

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _get_value(data: dict, key: str) -> Any:
        """Extract a value from nested Gemini extraction format."""
        entry = data.get(key)
        if entry is None:
            return None
        if isinstance(entry, dict):
            val = entry.get("value")
            return val if val is not None else None
        return entry

    @staticmethod
    def _get_required_font_height(area_cm2: float) -> float:
        """Return required font height in mm based on Rule 23 Table 1."""
        for max_area, general_h, _ in PDP_FONT_THRESHOLDS:
            if area_cm2 <= max_area:
                return general_h
        return 6.0

    @staticmethod
    def _validate_unit(unit: Optional[str]) -> Optional[ViolationRecord]:
        """Check if the net quantity unit is in legal SI format."""
        if unit is None:
            return None

        unit_lower = unit.lower().strip()
        all_legal = (
            LEGAL_WEIGHT_UNITS | LEGAL_VOLUME_UNITS
            | LEGAL_LENGTH_UNITS | LEGAL_COUNT_UNITS
        )

        if unit_lower in {u.lower() for u in all_legal}:
            return None

        # Check if it's a known illegal abbreviation
        if unit_lower in ILLEGAL_UNIT_MAP:
            correct = ILLEGAL_UNIT_MAP[unit_lower]
            return ViolationRecord(
                rule_reference=rule("NET_QUANTITY_UNIT_FORMAT").citation,
                act_section=rule("NET_QUANTITY_UNIT_FORMAT").obligation_section,
                punishment_section=rule("NET_QUANTITY_UNIT_FORMAT").ladder.section,
                statutory_penalty=PENALTY_SEC_29,
                field_name="Net Quantity Unit Format",
                severity="major",
                description=(
                    f"Non-standard unit abbreviation '{unit}' used. "
                    f"Must use standard SI unit '{correct}' as per LMPC Rules."
                ),
                expected_value=correct,
                found_value=unit,
                legal_proof_summary=(
                    f"Section 11(1)(d) of the Legal Metrology Act, 2009 explicitly prohibits quoting or "
                    f"indicating net quantity in non-standard units or unauthorized abbreviations (such as '{unit}'). "
                    f"Under the Jan Vishwas Act, 2026, first contraventions attract an Improvement Notice under Section 15(6)."
                ),
            )

        return ViolationRecord(
            rule_reference=rule("NET_QUANTITY_UNIT_FORMAT").citation,
            act_section=rule("NET_QUANTITY_UNIT_FORMAT").obligation_section,
            punishment_section=rule("NET_QUANTITY_UNIT_FORMAT").ladder.section,
            statutory_penalty=PENALTY_SEC_29,
            field_name="Net Quantity Unit Format",
            severity="major",
            description=f"Unrecognized unit '{unit}'. Must use standard SI units (g, kg, ml, l, cm, m).",
            found_value=unit,
            legal_proof_summary="Indicating net quantity in unauthorized units violates Section 11(1)(d) of Legal Metrology Act, 2009.",
        )

    @staticmethod
    def _compute_usp(
        mrp_str: Optional[str],
        net_value: Any,
        net_unit: Optional[str],
    ) -> Optional[str]:
        """
        Compute the legally required Unit Sale Price.

        USP = MRP / Net Quantity (in base units)
        - Packages > 1 kg or 1 L → price per kg or per L
        - Packages < 1 kg or 1 L → price per g or per ml
        """
        if mrp_str is None or net_value is None or net_unit is None:
            return None

        try:
            mrp = float(re.sub(r"[^\d.]", "", str(mrp_str)))
            qty = float(net_value)
        except (ValueError, TypeError):
            return None

        if qty <= 0:
            return None

        unit_lower = net_unit.lower().strip()

        # Determine base unit and compute rate
        if unit_lower in {"g", "gm", "gms", "gram", "grams"}:
            if qty > 1000:
                rate = mrp / (qty / 1000)
                return f"₹{rate:.2f} per kg"
            else:
                rate = mrp / qty
                return f"₹{rate:.2f} per g"
        elif unit_lower in {"kg", "kgs", "kilos"}:
            rate = mrp / qty
            return f"₹{rate:.2f} per kg"
        elif unit_lower in {"ml", "mls", "millilitre"}:
            if qty > 1000:
                rate = mrp / (qty / 1000)
                return f"₹{rate:.2f} per l"
            else:
                rate = mrp / qty
                return f"₹{rate:.2f} per ml"
        elif unit_lower in {"l", "ltr", "ltrs", "litre", "litres"}:
            rate = mrp / qty
            return f"₹{rate:.2f} per l"
        elif unit_lower in {"m", "cm", "mm"}:
            # Normalize to meters
            if unit_lower == "cm":
                qty_m = qty / 100
            elif unit_lower == "mm":
                qty_m = qty / 1000
            else:
                qty_m = qty
            rate = mrp / qty_m
            return f"₹{rate:.2f} per m"
        else:
            # Count-based
            rate = mrp / qty
            return f"₹{rate:.2f} per unit"

    @staticmethod
    def _check_cross_modal_discrepancies(
        extractions: dict[str, Any],
        listing_data: dict[str, Any],
    ) -> list[ViolationRecord]:
        """
        Compare physical packaging OCR data against e-commerce listing data
        to detect deceptive practices.
        """
        violations: list[ViolationRecord] = []

        # --- Price Overcharge Detection ---
        packaging_mrp = extractions.get("mrp", {})
        if isinstance(packaging_mrp, dict):
            packaging_mrp = packaging_mrp.get("value")

        listing_price = listing_data.get("listed_price")

        if packaging_mrp and listing_price:
            try:
                pkg_mrp_val = float(re.sub(r"[^\d.]", "", str(packaging_mrp)))
                lst_price_val = float(re.sub(r"[^\d.]", "", str(listing_price)))

                if lst_price_val > pkg_mrp_val:
                    violations.append(ViolationRecord(
                        rule_reference="Section 18 - Legal Metrology Act, 2009",
                        act_section="Section 18(1) - Legal Metrology Act, 2009",
                        punishment_section="Section 36(1) - Legal Metrology Act, 2009",
                        statutory_penalty=PENALTY_SEC_36_1,
                        field_name="Price Overcharge (MRP Violation)",
                        severity="critical",
                        description=(
                            f"E-commerce listing price (₹{lst_price_val:.2f}) "
                            f"EXCEEDS printed packaging MRP (₹{pkg_mrp_val:.2f}). "
                            f"Selling above MRP is a criminal statutory offence under the "
                            f"Legal Metrology Act, 2009."
                        ),
                        expected_value=f"≤ ₹{pkg_mrp_val:.2f}",
                        found_value=f"₹{lst_price_val:.2f}",
                        is_discrepancy=True,
                        legal_proof_summary=(
                            f"Direct criminal contravention of Section 18(1) of the Legal Metrology Act, 2009. "
                            f"The marketplace/seller is overcharging by ₹{lst_price_val - pkg_mrp_val:.2f} above declared MRP."
                        ),
                    ))
            except (ValueError, TypeError):
                pass

        # --- Country of Origin Mismatch ---
        pkg_country = extractions.get("country_of_origin", {})
        if isinstance(pkg_country, dict):
            pkg_country = pkg_country.get("value")
        lst_country = listing_data.get("country_of_origin")

        if pkg_country and lst_country:
            if pkg_country.lower().strip() != lst_country.lower().strip():
                violations.append(ViolationRecord(
                    rule_reference="Rule 6(1)(aa) & Consumer Protection (E-Commerce) Rules, 2020",
                    act_section="Section 18(1) - Legal Metrology Act, 2009",
                    punishment_section="Section 36(1) - Legal Metrology Act, 2009",
                    statutory_penalty=PENALTY_SEC_36_1,
                    field_name="Country of Origin Mismatch",
                    severity="critical",
                    description=(
                        f"Country of Origin on packaging ('{pkg_country}') "
                        f"does not match e-commerce listing ('{lst_country}'). "
                        f"This constitutes a deceptive trade practice."
                    ),
                    expected_value=pkg_country,
                    found_value=lst_country,
                    is_discrepancy=True,
                    legal_proof_summary=(
                        "Deceptive trade practice under Section 18(1) of Legal Metrology Act, 2009 and "
                        "Consumer Protection (E-Commerce) Rules, 2020. Misleading consumers about product origin."
                    ),
                ))

        # --- Net Quantity Mismatch ---
        pkg_net = extractions.get("net_quantity", {})
        if isinstance(pkg_net, dict):
            pkg_net = pkg_net.get("value")
        lst_net = listing_data.get("net_quantity")

        if pkg_net and lst_net:
            if str(pkg_net).strip().lower() != str(lst_net).strip().lower():
                violations.append(ViolationRecord(
                    rule_reference="Rule 6(1)(c) & Consumer Protection (E-Commerce) Rules, 2020",
                    act_section="Section 18(2) - Legal Metrology Act, 2009",
                    punishment_section="Section 36(1) - Legal Metrology Act, 2009",
                    statutory_penalty=PENALTY_SEC_36_1,
                    field_name="Net Quantity Mismatch",
                    severity="major",
                    description=(
                        f"Net Quantity on packaging ('{pkg_net}') "
                        f"differs from e-commerce listing ('{lst_net}')."
                    ),
                    expected_value=str(pkg_net),
                    found_value=str(lst_net),
                    is_discrepancy=True,
                    legal_proof_summary=(
                        "Section 18(2) of Legal Metrology Act, 2009 mandates that any advertisement or listing "
                        "mentioning retail price must state the accurate net quantity."
                    ),
                ))

        return violations


# Module-level singleton
lmpc_evaluator = LMPCEvaluator()
