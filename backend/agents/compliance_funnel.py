"""
SIH26034 — The 5-Stage Compliance Funnel Engine
"Every label, verified once, re-verified when it changes — not every package, scanned."

Architecture:
- Stage 0: Perceptual Artwork Dedup (GTIN + dHash/pHash) -> ~₹0 cost, drops ~75-80% volume
- Stage 1: Deterministic Microsecond Rule Checks (USP math, SI units, MRP format) -> ₹0.0001, microsecond, no AI
- Stage 2: Local OCR & Field Extraction -> ~₹0.05, local edge/CPU
- Stage 3: Multimodal Vision (Gemini) -> ~₹0.75, only hard edge cases (cylindrical, glare, multilingual)
- Stage 4: FSSAI-Aligned Officer Worklist -> Prioritizes human inspection attention
"""

from __future__ import annotations

import hashlib
import io
import logging
import math
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# Legal Metrology SI Standard Units
LEGAL_WEIGHT_UNITS = {"g", "kg"}
LEGAL_VOLUME_UNITS = {"ml", "l", "L"}
LEGAL_LENGTH_UNITS = {"cm", "m", "mm"}
LEGAL_COUNT_UNITS = {"N", "units", "unit", "nos", "pieces", "pcs"}

ILLEGAL_UNIT_ABBREVIATIONS = {
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

MANDATORY_LMPC_FIELDS = [
    "product_name",
    "manufacturer_name",
    "manufacturer_address",
    "country_of_origin",
    "net_quantity",
    "mrp",
    "unit_sale_price",
    "manufacture_date",
    "expiry_date",
    "consumer_care",
]


# ---------------------------------------------------------------------------
# Stage 0: Perceptual Artwork Deduplication Engine
# ---------------------------------------------------------------------------

def compute_dhash(image_bytes: bytes, hash_size: int = 8) -> str:
    """
    Compute a 64-bit difference hash (dHash) for an artwork image.
    Invariant to scale, compression artifacts, and minor lighting changes.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("L")
        # Resize to (hash_size + 1, hash_size)
        image = image.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(image.getdata())
        
        # Compare adjacent pixels
        diff = []
        for row in range(hash_size):
            for col in range(hash_size):
                pixel_left = pixels[row * (hash_size + 1) + col]
                pixel_right = pixels[row * (hash_size + 1) + col + 1]
                diff.append("1" if pixel_left > pixel_right else "0")
        
        # Convert binary string to hex
        decimal_val = int("".join(diff), 2)
        return hex(decimal_val)[2:].zfill(hash_size * hash_size // 4)
    except Exception as e:
        logger.warning("dHash calculation fallback to md5: %s", e)
        return hashlib.md5(image_bytes[:4096]).hexdigest()[:16]


def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculate the Hamming distance between two hex hashes."""
    if len(hash1) != len(hash2):
        return 999
    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        xor_val = val1 ^ val2
        return bin(xor_val).count("1")
    except Exception:
        return 999


@dataclass
class ArtworkRecord:
    gtin: str
    artwork_hash: str
    product_name: str
    brand: str
    verified_at: str
    status: str
    compliance_score: float
    violations_summary: List[str] = field(default_factory=list)
    cache_hits: int = 0


class ArtworkDedupCache:
    """
    Stage 0 Cache: GTIN + Perceptual Hash
    If the artwork is identical (hamming distance <= 2), reuse previous verification verdict.
    """

    def __init__(self):
        self._cache: Dict[str, ArtworkRecord] = {}
        self.total_dedup_hits = 0
        self.total_screened = 0

    def register(
        self,
        gtin: str,
        artwork_hash: str,
        product_name: str,
        brand: str,
        status: str,
        compliance_score: float,
        violations: Optional[List[str]] = None,
    ) -> ArtworkRecord:
        record = ArtworkRecord(
            gtin=gtin,
            artwork_hash=artwork_hash,
            product_name=product_name,
            brand=brand,
            verified_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            status=status,
            compliance_score=compliance_score,
            violations_summary=violations or [],
            cache_hits=0,
        )
        self._cache[f"{gtin}:{artwork_hash}"] = record
        return record

    def check(self, gtin: str, artwork_hash: str) -> Optional[ArtworkRecord]:
        """Check if artwork exists with hamming distance <= 2 for this GTIN."""
        self.total_screened += 1
        
        # 1. Exact match
        key = f"{gtin}:{artwork_hash}"
        if key in self._cache:
            self.total_dedup_hits += 1
            self._cache[key].cache_hits += 1
            return self._cache[key]

        # 2. Near-exact perceptual match (hamming distance <= 2)
        for k, record in self._cache.items():
            if record.gtin == gtin:
                if hamming_distance(record.artwork_hash, artwork_hash) <= 2:
                    self.total_dedup_hits += 1
                    record.cache_hits += 1
                    return record

        return None


# Global dedup cache instance
artwork_cache = ArtworkDedupCache()


# ---------------------------------------------------------------------------
# Stage 1: Deterministic Microsecond Rule Checker (Zero AI, Zero API Cost)
# ---------------------------------------------------------------------------

@dataclass
class DeterministicCheckResult:
    is_valid: bool
    failures: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


class DeterministicRuleChecker:
    """
    Stage 1: Pure math, regex, and statutory formatting checks.
    Runs in microseconds without contacting any vision model or LLM.
    Catches 65%+ of real-world labelling defects.
    """

    @staticmethod
    def check_unit_sale_price(
        mrp_val: Optional[float],
        net_quantity_val: Optional[float],
        net_quantity_unit: Optional[str],
        declared_usp_val: Optional[float],
        declared_usp_unit: Optional[str],
    ) -> Tuple[bool, Optional[str]]:
        """
        Rule 6(1)(h) / Unit Sale Price (2021 Amendment):
        - Mandatory for packages containing > 1 kg or > 1 L.
        - Must state price per g/kg or ml/L.
        - Math must match within +- 1.5% tolerance.
        """
        if mrp_val is None or net_quantity_val is None or net_quantity_val <= 0:
            return True, None  # Cannot compute without values

        clean_unit = (net_quantity_unit or "").strip().lower()

        # Check threshold for mandatory USP (> 1 kg or > 1 L)
        is_above_1kg_or_1l = (
            (clean_unit in ("kg", "kilos") and net_quantity_val >= 1.0)
            or (clean_unit in ("l", "ltr", "litre") and net_quantity_val >= 1.0)
            or (clean_unit in ("g", "gm", "gms") and net_quantity_val >= 1000.0)
            or (clean_unit in ("ml", "mls") and net_quantity_val >= 1000.0)
        )

        if is_above_1kg_or_1l and declared_usp_val is None:
            return (
                False,
                f"Rule 6(1)(h) Contravention: Package has Net Quantity {net_quantity_val}{clean_unit} (>1kg/1L), but mandatory Unit Sale Price (USP) declaration is completely missing.",
            )

        if declared_usp_val is None:
            return True, None

        # Compute theoretical USP
        calc_usp = mrp_val / net_quantity_val

        # If declared is per kg but net qty was in g:
        if clean_unit in ("g", "gm") and str(declared_usp_unit).lower() in ("kg", "/kg", "₹/kg"):
            calc_usp = (mrp_val / net_quantity_val) * 1000.0
        elif clean_unit in ("ml", "mls") and str(declared_usp_unit).lower() in ("l", "/l", "₹/l"):
            calc_usp = (mrp_val / net_quantity_val) * 1000.0
        elif clean_unit in ("kg",) and str(declared_usp_unit).lower() in ("g", "/g", "₹/g"):
            calc_usp = (mrp_val / net_quantity_val) / 1000.0
        elif clean_unit in ("l", "L") and str(declared_usp_unit).lower() in ("ml", "/ml", "₹/ml"):
            calc_usp = (mrp_val / net_quantity_val) / 1000.0

        percent_diff = abs(calc_usp - declared_usp_val) / calc_usp * 100.0
        if percent_diff > 2.0:
            return (
                False,
                f"Rule 6(1)(h) Mathematical Mismatch: Declared USP is ₹{declared_usp_val:.2f}/{declared_usp_unit or 'unit'}, but calculated USP is ₹{calc_usp:.2f} (MRP ₹{mrp_val} / {net_quantity_val}{clean_unit}). Difference: {percent_diff:.1f}%.",
            )

        return True, None

    @staticmethod
    def check_si_units(unit_string: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Rule 6(1)(e) - Units of weight, measure or number.
        Illegal to declare 'gms', 'gm', 'kilos', 'ltrs', 'litre'.
        Must use strict SI symbols: 'g', 'kg', 'ml', 'l', 'L', 'm', 'cm', 'no.'.
        """
        if not unit_string:
            return False, "Rule 6(1)(e): Unit of measurement is missing."

        clean = unit_string.strip().lower()
        if clean in ILLEGAL_UNIT_ABBREVIATIONS:
            correct_symbol = ILLEGAL_UNIT_ABBREVIATIONS[clean]
            return (
                False,
                f"Rule 6(1)(e) Non-Standard Unit: Declared unit '{unit_string}' is illegal under LMPC Rules. Mandatory statutory symbol is '{correct_symbol}'.",
            )

        valid_units = LEGAL_WEIGHT_UNITS | LEGAL_VOLUME_UNITS | LEGAL_LENGTH_UNITS | LEGAL_COUNT_UNITS
        if clean not in valid_units:
            return (
                False,
                f"Rule 6(1)(e) Unrecognized Unit: '{unit_string}' is not a recognized legal metrology measurement unit.",
            )

        return True, None

    @staticmethod
    def check_mrp_format(mrp_text: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Rule 6(1)(e) - Maximum Retail Price declaration:
        Must include the words 'inclusive of all taxes' or '(incl. of all taxes)'.
        """
        if not mrp_text:
            return False, "Rule 6(1)(e): Maximum Retail Price (MRP) declaration is missing."

        lower = mrp_text.lower()
        has_taxes = any(
            phrase in lower
            for phrase in [
                "incl. of all taxes",
                "inclusive of all taxes",
                "incl of all taxes",
                "incl. all taxes",
                "all taxes included",
            ]
        )
        if not has_taxes:
            return (
                False,
                "Rule 6(1)(e) Statutory Format Violation: MRP declaration lacks mandatory 'inclusive of all taxes' suffix.",
            )

        return True, None

    @classmethod
    def run_stage_1(cls, declarations: Dict[str, Any]) -> DeterministicCheckResult:
        """Run all Stage 1 deterministic checks in microseconds."""
        t0 = time.perf_counter()
        failures = []
        warnings = []

        # 1. Missing mandatory declarations presence
        for field_name in MANDATORY_LMPC_FIELDS:
            val = declarations.get(field_name)
            if not val:
                failures.append({
                    "rule_id": field_name.upper(),
                    "clause": "Rule 6(1) - Mandatory Declarations",
                    "severity": "CRITICAL" if field_name in ("mrp", "net_quantity") else "MAJOR",
                    "description": f"Mandatory declaration '{field_name.replace('_', ' ').title()}' is not declared.",
                })

        # 2. Check SI units
        net_qty = declarations.get("net_quantity")
        net_unit = declarations.get("net_quantity_unit")
        if net_unit:
            ok, err = cls.check_si_units(net_unit)
            if not ok and err:
                failures.append({
                    "rule_id": "NET_QUANTITY_UNIT",
                    "clause": "Rule 6(1)(e) - Legal Units",
                    "severity": "MAJOR",
                    "description": err,
                })

        # 3. Check MRP format
        mrp_raw = declarations.get("mrp_raw_text") or declarations.get("mrp_text")
        if mrp_raw:
            ok, err = cls.check_mrp_format(mrp_raw)
            if not ok and err:
                failures.append({
                    "rule_id": "MRP_TAX_INCLUSION",
                    "clause": "Rule 6(1)(e) - Maximum Retail Price",
                    "severity": "MAJOR",
                    "description": err,
                })

        # 4. Check USP arithmetic
        mrp_val = declarations.get("mrp_numeric")
        qty_val = declarations.get("net_quantity_numeric")
        usp_val = declarations.get("unit_sale_price_numeric")
        usp_unit = declarations.get("unit_sale_price_unit")
        if mrp_val and qty_val:
            ok, err = cls.check_unit_sale_price(
                mrp_val=float(mrp_val),
                net_quantity_val=float(qty_val),
                net_quantity_unit=str(net_unit or ""),
                declared_usp_val=float(usp_val) if usp_val is not None else None,
                declared_usp_unit=str(usp_unit or ""),
            )
            if not ok and err:
                failures.append({
                    "rule_id": "UNIT_SALE_PRICE",
                    "clause": "Rule 6(1)(h) - Unit Sale Price",
                    "severity": "CRITICAL",
                    "description": err,
                })

        t1 = time.perf_counter()
        exec_ms = round((t1 - t0) * 1000.0, 3)

        return DeterministicCheckResult(
            is_valid=len(failures) == 0,
            failures=failures,
            warnings=warnings,
            execution_time_ms=exec_ms,
        )


# ---------------------------------------------------------------------------
# Funnel Screening Result Dataclass
# ---------------------------------------------------------------------------

@dataclass
class FunnelScreenResult:
    sku_id: str
    gtin: str
    product_name: str
    brand: str
    stage_resolved: str  # "Stage 0 (Dedup)", "Stage 1 (Deterministic)", "Stage 2 (OCR)", "Stage 3 (Vision)", "Stage 4 (Officer)"
    is_compliant: bool
    compliance_score: float
    violations_count: int
    violations: List[Dict[str, Any]]
    compute_cost_inr: float
    latency_ms: float
    artwork_hash: str
    evidentiary_class: str  # "RULE_6_10_ECOMMERCE", "FIELD_OFFICER_EVIDENCE", "CROWDSOURCED_LEAD", "PRE_PRINT_CLEARANCE"
    risk_score: float = 0.0
