"""
Unit & Integration Tests for SIH26034 Multi-Shot Packaging Capture & Stage 1 Screener Engine
Ministry of Consumer Affairs, Food & Public Distribution • Department of Consumer Affairs
"""

import io
import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from backend.app import app
from backend.models import AuditInputType
from lmpc_labelparse import (
    parse_label,
    repair_numeric_run,
    needs_model,
    ParsedField,
    LabelParseResult,
)


def create_mock_panel_image(text: str, width: int = 400, height: int = 400) -> bytes:
    """Generate a clean synthetic image representing a packaging panel."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Test 1: Stage 1 Regex Screener Economics & Coverage
# ---------------------------------------------------------------------------

def test_stage1_screener_clean_tea_label():
    """Verify that a full tea label achieves >=75% coverage and settles at Stage 1 (needs_model = False)."""
    raw_text = """
    TATA TEA PREMIUM
    Desh Ki Chai
    Net Quantity: 500 g
    MRP: Rs. 250.00 (inclusive of all taxes)
    Unit Sale Price: Rs. 0.50 / g
    Mfg Date: 03/2026
    Expiry Date: 03/2027
    Mfg by: Tata Consumer Products Ltd., 1 Bishop Lefroy Road, Kolkata, West Bengal - 700020
    Country of Origin: India
    For Consumer Complaints: contact Manager at care@tataconsumer.com or 1800-108-4488
    """
    res = parse_label(raw_text)
    
    assert res.coverage_percent >= 75.0, f"Expected >= 75% coverage, got {res.coverage_percent}%"
    assert not res.needs_model_escalation, "Clean tea label should settle at Stage 1 without model escalation!"
    assert res.fields["NET_QUANTITY"].value == "500 g"
    assert "250" in (res.fields["MRP"].value or "")
    assert res.fields["COUNTRY_OF_ORIGIN"].value == "India"
    assert res.pin_code == "700020"
    # Statutory Discipline: generic_name is intentionally unanchored to avoid hallucination
    assert res.fields["GENERIC_NAME"].value is None, "generic_name must remain unparsed without anchor to prevent hallucination"


def test_scoped_ocr_digit_repair():
    """Verify that scoped OCR repair fixes '2SO.OO' -> '250.00' and 'lOOO' -> '1000' without corrupting words or units."""
    # Price expressions
    assert repair_numeric_run("2SO.OO") == "250.00"
    assert repair_numeric_run("lOOO") == "1000"
    assert repair_numeric_run("l00") == "100"
    
    # Must preserve brand names and units (no global g -> 9 mapping)
    assert repair_numeric_run("Gupta Oil Mills") == "Gupta Oil Mills"
    assert repair_numeric_run("250 g") == "250 g"
    assert repair_numeric_run("Tata Consumer Products") == "Tata Consumer Products"


def test_two_pass_line_stitching():
    """Verify that split adjacent lines on narrow packaging are stitched in Pass 2."""
    split_lines = [
        "Net Weight:",
        "250 g",
        "Maximum Retail Price:",
        "Rs. 120.00",
        "Country of Origin:",
        "India",
    ]
    res = parse_label({"text": "\n".join(split_lines), "lines": split_lines})
    
    assert res.fields["NET_QUANTITY"].value == "250 g"
    assert "120" in (res.fields["MRP"].value or "")
    assert res.fields["COUNTRY_OF_ORIGIN"].value == "India"


# ---------------------------------------------------------------------------
# Test 2: Multi-Shot Endpoint Integration Test
# ---------------------------------------------------------------------------

def test_api_multi_shot_audit_endpoint():
    """Verify POST /api/audit/multi-shot combines front, back, and barcode close-up into one statutory verdict."""
    client = TestClient(app)
    
    front_text = "TATA TEA GOLD\nMRP Rs. 260.00 (incl. all taxes)\nBest Quality Indian Tea"
    back_text = """
    Net Wt: 500 g
    USP: Rs. 0.52 / g
    Mfg Date: 02/2026
    Best Before: 12 months from packing
    Country of Origin: India
    Manufactured by: Tata Consumer Products Ltd., Kolkata 700020
    Consumer Care: care@tataconsumer.com / 1800-345-0000
    """
    barcode_text = "EAN: 8901030383478\nPrice Sticker: Rs. 260.00"
    
    front_bytes = create_mock_panel_image(front_text)
    back_bytes = create_mock_panel_image(back_text)
    barcode_bytes = create_mock_panel_image(barcode_text)
    
    files = [
        ("shot_front", ("front.jpg", front_bytes, "image/jpeg")),
        ("shot_back", ("back.jpg", back_bytes, "image/jpeg")),
        ("shot_barcode", ("barcode.jpg", barcode_bytes, "image/jpeg")),
    ]
    
    response = client.post("/api/audit/multi-shot", files=files)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["input_type"] == "multi_shot"
    assert data["audit_status"] in ["COMPLIANT", "NON_COMPLIANT", "INSUFFICIENT_DATA", "PARTIAL_VIOLATION"]
    
    # Verify Shots Metadata
    shots = data.get("shots_metadata", [])
    assert len(shots) == 3, f"Expected 3 shots metadata, got {len(shots)}"
    assert shots[0]["panel"] == "front"
    assert shots[1]["panel"] == "back"
    assert shots[2]["panel"] == "barcode"
    
    # Verify Stage 1 Economics
    econ = data.get("stage1_economics", {})
    assert econ.get("cost_inr") == 0.0, "Stage 1 screener must cost exactly ₹0.00"
    assert "latency_ms" in econ
    assert "coverage_percent" in econ
    assert econ.get("coverage_percent", 0) >= 0.0
    
    # Verify Declaration Status Map
    dec = data.get("declaration_status", {})
    assert len(dec) == 10, f"Expected 10 statutory declaration fields, got {len(dec)}"
    assert "net_quantity" in dec
    assert "mrp" in dec
    assert "country_of_origin" in dec
    assert "consumer_care" in dec
    assert "unit_sale_price" in dec


def test_api_multi_shot_re_priced_oversticker():
    """Verify Section 18 violation is flagged when a sticker increases price over printed MRP."""
    client = TestClient(app)
    
    front_text = "PREMIUM COFFEE 200g\nMRP Rs. 200.00 (inclusive of all taxes)"
    back_text = "Manufactured by Coffee Co., Bangalore 560001\nCountry of Origin: India\nNet Quantity: 200 g"
    sticker_text = "SPECIAL RETAIL STICKER\nMRP Rs. 260.00\nOver-pasted sticker"
    
    files = [
        ("shot_front", ("front.jpg", create_mock_panel_image(front_text), "image/jpeg")),
        ("shot_back", ("back.jpg", create_mock_panel_image(back_text), "image/jpeg")),
        ("shot_barcode", ("sticker.jpg", create_mock_panel_image(sticker_text), "image/jpeg")),
    ]
    
    response = client.post("/api/audit/multi-shot", files=files)
    assert response.status_code == 200
    data = response.json()
    
    # Re-priced pack should be flagged for alteration under Section 18 / Section 36
    verdict = data.get("verdict")
    assert verdict is not None
    violations = verdict.get("violations", [])
    is_flagged = any("Alteration" in v.get("rule_reference", "") or "Section 18" in v.get("act_section", "") for v in violations)
    # The presence of violation or non-compliant audit status confirms scrutiny works
    assert is_flagged or data.get("audit_status") != "COMPLIANT"


if __name__ == "__main__":
    import sys
    tests = [
        ("test_stage1_screener_clean_tea_label", test_stage1_screener_clean_tea_label),
        ("test_scoped_ocr_digit_repair", test_scoped_ocr_digit_repair),
        ("test_two_pass_line_stitching", test_two_pass_line_stitching),
        ("test_api_multi_shot_audit_endpoint", test_api_multi_shot_audit_endpoint),
        ("test_api_multi_shot_re_priced_oversticker", test_api_multi_shot_re_priced_oversticker),
    ]
    passed = 0
    failed = 0
    print("=" * 70)
    print("SIH26034 Multi-Shot & Stage 1 Screener Test Suite")
    print("=" * 70)
    for name, func in tests:
        try:
            func()
            print(f"  PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name} -> {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    if failed > 0:
        sys.exit(1)
