"""
Unit & Integration Tests for the SIH26034 5-Stage Compliance Funnel Engine
"""

import unittest
from backend.agents.compliance_funnel import (
    ArtworkDedupCache,
    compute_dhash,
    hamming_distance,
    DeterministicRuleChecker,
)
from backend.agents.officer_worklist import (
    RiskScoringEngine,
    OfficerWorklistItem,
    OfficerWorklistManager,
)
from backend.data.maharashtra_spices_dataset import (
    PILOT_SLICE_INFO,
    EVALUATION_BENCHMARK_RESULTS,
)


# ---------------------------------------------------------------------------
# Test 1: Stage 0 Perceptual Deduplication
# ---------------------------------------------------------------------------

def test_dhash_and_hamming_distance():
    # Create mock 10x10 byte streams
    from PIL import Image
    import io

    img1 = Image.new("L", (100, 100), color=128)
    buf1 = io.BytesIO()
    img1.save(buf1, format="PNG")
    bytes1 = buf1.getvalue()

    # Slightly modified image
    img2 = Image.new("L", (100, 100), color=130)
    buf2 = io.BytesIO()
    img2.save(buf2, format="PNG")
    bytes2 = buf2.getvalue()

    hash1 = compute_dhash(bytes1)
    hash2 = compute_dhash(bytes2)

    dist = hamming_distance(hash1, hash2)
    assert dist <= 2, f"Expected near-identical hash distance <= 2, got {dist}"


def test_artwork_dedup_cache():
    cache = ArtworkDedupCache()
    gtin = "8901248010219"
    hash_val = "a1b2c3d4e5f60718"

    # Register artwork
    cache.register(
        gtin=gtin,
        artwork_hash=hash_val,
        product_name="Everest Garam Masala 100g",
        brand="Everest",
        status="COMPLIANT",
        compliance_score=100.0,
    )

    # First lookup: exact hit
    hit = cache.check(gtin, hash_val)
    assert hit is not None
    assert hit.product_name == "Everest Garam Masala 100g"
    assert cache.total_dedup_hits == 1

    # Second lookup: different GTIN -> miss
    miss = cache.check("8909999999999", hash_val)
    assert miss is None


# ---------------------------------------------------------------------------
# Test 2: Stage 1 Deterministic Rule Checks (Zero AI, Microseconds)
# ---------------------------------------------------------------------------

def test_unit_sale_price_math():
    # Package > 1kg: 1000g, MRP 200, USP declared 0.20/g -> MATCH
    ok, err = DeterministicRuleChecker.check_unit_sale_price(
        mrp_val=200.0,
        net_quantity_val=1000.0,
        net_quantity_unit="g",
        declared_usp_val=0.20,
        declared_usp_unit="g",
    )
    assert ok is True
    assert err is None

    # Package > 1kg: Missing USP -> CONTRAVENTION
    ok_missing, err_missing = DeterministicRuleChecker.check_unit_sale_price(
        mrp_val=250.0,
        net_quantity_val=1.5,
        net_quantity_unit="kg",
        declared_usp_val=None,
        declared_usp_unit=None,
    )
    assert ok_missing is False
    assert "Rule 6(1)(h)" in err_missing

    # Mathematical mismatch: MRP 100 for 500g, but declared USP 0.40/g instead of 0.20/g
    ok_bad_math, err_bad_math = DeterministicRuleChecker.check_unit_sale_price(
        mrp_val=100.0,
        net_quantity_val=500.0,
        net_quantity_unit="g",
        declared_usp_val=0.40,
        declared_usp_unit="g",
    )
    assert ok_bad_math is False
    assert "Mathematical Mismatch" in err_bad_math


def test_si_units_validation():
    # Legal SI units
    assert DeterministicRuleChecker.check_si_units("g")[0] is True
    assert DeterministicRuleChecker.check_si_units("kg")[0] is True
    assert DeterministicRuleChecker.check_si_units("ml")[0] is True
    assert DeterministicRuleChecker.check_si_units("l")[0] is True

    # Illegal colloquial abbreviations
    ok_gms, err_gms = DeterministicRuleChecker.check_si_units("gms")
    assert ok_gms is False
    assert "Rule 6(1)(e)" in err_gms
    assert "'g'" in err_gms

    ok_ltr, err_ltr = DeterministicRuleChecker.check_si_units("ltrs")
    assert ok_ltr is False
    assert "Rule 6(1)(e)" in err_ltr


def test_mrp_format_check():
    # Compliant MRP format
    assert DeterministicRuleChecker.check_mrp_format("MRP Rs 99.00 (inclusive of all taxes)")[0] is True
    assert DeterministicRuleChecker.check_mrp_format("Rs. 150.00 incl. of all taxes")[0] is True

    # Missing taxes statement
    ok, err = DeterministicRuleChecker.check_mrp_format("MRP Rs 99.00")
    assert ok is False
    assert "inclusive of all taxes" in err


# ---------------------------------------------------------------------------
# Test 3: Stage 4 FSSAI-Aligned Risk Scoring & Worklist
# ---------------------------------------------------------------------------

def test_risk_scoring_calculation():
    # High risk: Edible oil with critical violation and brand recidivism
    risk_high = RiskScoringEngine.calculate_risk(
        category="edible_oil",
        brand="Unbranded Loose Packer",
        violations=[{"rule_id": "MRP", "severity": "CRITICAL"}],
        evidentiary_class="OFFICER_INSPECTION_EVIDENCE",
        complaint_count=5,
    )
    assert risk_high >= 80.0, f"Expected high risk >= 80, got {risk_high}"

    # Low risk: Confectionery with no violations and e-com evidence
    risk_low = RiskScoringEngine.calculate_risk(
        category="confectionery_snacks",
        brand="Tata Consumer",
        violations=[],
        evidentiary_class="RULE_6_10_ECOMMERCE",
        complaint_count=0,
    )
    assert risk_low < 45.0, f"Expected low risk < 45, got {risk_low}"


# ---------------------------------------------------------------------------
# Test 4: Maharashtra Pilot & Benchmark Integrity
# ---------------------------------------------------------------------------

def test_pilot_dataset_integrity():
    assert PILOT_SLICE_INFO["funnel_metrics"]["total_screened_skus"] == 5000
    assert PILOT_SLICE_INFO["funnel_metrics"]["stage_0_dedup_hits"] == 3850
    assert PILOT_SLICE_INFO["cost_curve"]["blended_average_cost_per_sku_inr"] < 0.05
    assert len(EVALUATION_BENCHMARK_RESULTS["per_field_metrics"]) >= 7
    assert EVALUATION_BENCHMARK_RESULTS["macro_f1_score"] >= 95.0
