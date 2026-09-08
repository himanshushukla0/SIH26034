"""
SIH26034 — FSSAI-Aligned Risk Scorer & Officer Worklist Engine
Prioritizes scarce Legal Metrology Officer inspection capacity by regulatory risk.

Principles:
1. Target by risk, not uniformly (mirrors FSSAI risk-categorisation model).
2. Evidentiary taxonomy:
   - RULE_6_10_ECOMMERCE: Evidence against e-commerce platform/seller (Rule 6(10)).
   - CROWDSOURCED_LEAD: Investigatory lead only (no chain of custody, never solo evidence).
   - OFFICER_INSPECTION_EVIDENCE: Statutory evidence supporting Section 15(6) or Section 39 notices.
   - PRE_PRINT_CLEARANCE: Brand pre-print upload, earns inspection deprioritization.
3. The output is a ranked officer worklist, not an unranked scoreboard.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Category Base Risk Weights (FSSAI Risk Categorization Matrix)
CATEGORY_RISK_WEIGHTS: Dict[str, float] = {
    "infant_food": 1.00,
    "baby_formula": 1.00,
    "edible_oil": 0.85,
    "mustard_oil": 0.85,
    "ghee": 0.85,
    "spices_condiments": 0.80,
    "packaged_spices": 0.80,
    "dairy": 0.75,
    "perishables": 0.65,
    "staples_flour_rice": 0.60,
    "beverages_tea": 0.50,
    "confectionery_snacks": 0.45,
    "general_fmcg": 0.40,
}

# Known recidivist brands with higher historic non-compliance rates in enforcement blitzes
RECIDIVIST_BRAND_MULTIPLIERS: Dict[str, float] = {
    "unbranded_loose_packer": 1.50,
    "regional_private_label": 1.35,
    "imported_unregistered": 1.40,
    "patanjali": 1.15,
    "badshah": 1.10,
    "everest": 1.05,
    "mdh": 1.05,
    "fortune": 1.00,
    "dhara": 1.00,
    "tata": 0.90,
}


@dataclass
class OfficerWorklistItem:
    id: str
    sku_id: str
    gtin: str
    product_name: str
    brand: str
    category: str
    jurisdiction: str  # e.g., "Maharashtra - Pune Enforcement Zone"
    risk_score: float  # 0.0 to 100.0
    priority_level: str  # "HIGH", "MEDIUM", "LOW"
    evidentiary_class: str  # "RULE_6_10_ECOMMERCE", "OFFICER_INSPECTION_EVIDENCE", "CROWDSOURCED_LEAD"
    evidentiary_description: str
    violations: List[Dict[str, Any]]
    top_violation_clause: str
    statutory_action: str  # e.g., "Issue S.15(6) Improvement Notice", "Rule 6(10) E-Com Notice to Seller"
    estimated_penalty_inr: int
    draft_notice_ready: bool = True
    assigned_officer: Optional[str] = None
    created_at: str = ""


class RiskScoringEngine:
    """Computes FSSAI-aligned risk score for an inspected or screened SKU."""

    @staticmethod
    def calculate_risk(
        category: str,
        brand: str,
        violations: List[Dict[str, Any]],
        evidentiary_class: str,
        complaint_count: int = 1,
        is_new_artwork: bool = False,
    ) -> float:
        """
        Risk formula:
        R = (CategoryRisk * 35) + (BrandRecidivism * 25) + (SeverityScore * 25) + (ComplaintWeight * 10) + (Novelty * 5)
        Max score = 100.0
        """
        clean_cat = category.strip().lower().replace(" ", "_")
        cat_weight = CATEGORY_RISK_WEIGHTS.get(clean_cat, 0.50)

        # Brand multiplier
        clean_brand = brand.strip().lower()
        brand_mult = 1.0
        for b_key, mult in RECIDIVIST_BRAND_MULTIPLIERS.items():
            if b_key in clean_brand:
                brand_mult = mult
                break

        # Severity score
        sev_score = 0.0
        has_critical = any(v.get("severity", "").upper() == "CRITICAL" for v in violations)
        has_major = any(v.get("severity", "").upper() == "MAJOR" for v in violations)
        
        if has_critical:
            sev_score = 1.0
        elif has_major:
            sev_score = 0.70
        elif violations:
            sev_score = 0.40
        else:
            sev_score = 0.05

        # Evidentiary channel multiplier:
        # Officer evidence = highest weight, E-com = medium, Crowdsource = lower baseline until verified
        evi_mult = 1.0
        if evidentiary_class == "OFFICER_INSPECTION_EVIDENCE":
            evi_mult = 1.0
        elif evidentiary_class == "RULE_6_10_ECOMMERCE":
            evi_mult = 0.85
        elif evidentiary_class == "CROWDSOURCED_LEAD":
            evi_mult = 0.65  # No chain of custody, leads need officer confirmation

        # Complaint weight (1 to 10 scale)
        comp_score = min(complaint_count / 10.0, 1.0)

        # Novelty factor
        novelty_score = 1.0 if is_new_artwork else 0.2

        raw_score = (
            (cat_weight * 35.0)
            + (min(brand_mult, 1.5) * 20.0)
            + (sev_score * 30.0)
            + (comp_score * 10.0)
            + (novelty_score * 5.0)
        ) * evi_mult

        return round(min(max(raw_score, 5.0), 99.9), 1)


class OfficerWorklistManager:
    """Maintains and sorts the priority triage queue for field officers."""

    def __init__(self):
        self._worklist: List[OfficerWorklistItem] = []

    def add_item(self, item: OfficerWorklistItem):
        self._worklist.append(item)
        self._worklist.sort(key=lambda x: x.risk_score, reverse=True)

    def get_ranked_worklist(
        self,
        jurisdiction: Optional[str] = None,
        evidentiary_class: Optional[str] = None,
        min_priority: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        filtered = self._worklist

        if jurisdiction:
            filtered = [x for x in filtered if jurisdiction.lower() in x.jurisdiction.lower()]
        if evidentiary_class:
            filtered = [x for x in filtered if x.evidentiary_class == evidentiary_class]
        if min_priority:
            filtered = [x for x in filtered if x.priority_level == min_priority]

        return [asdict(x) for x in filtered[:limit]]

    def clear(self):
        self._worklist.clear()


# Global worklist instance
officer_worklist = OfficerWorklistManager()
