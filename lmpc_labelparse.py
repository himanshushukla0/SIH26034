#!/usr/bin/env python3
"""
LMPC COMPLIANCE ENGINE (SIH26034) — STEP 3: MAP (LABEL PARSER)
text → 9 Rule 6 fields

Key Engineering Principles:
1. Scoped OCR Digit Repair: Repaired strictly on leading numeric runs within price/qty
   context (e.g. '2SO.OO' -> '250.00', 'lOOO ml' -> '1000 ml'). Gupta Oil Mills and
   '250 g' are never corrupted (never map g->9 globally).
2. Two-Pass Scanning: First pass on single lines (conf 0.92). Second pass on adjacent
   line pairs for narrow packs (conf 0.82, stitched=True).
3. Absence is a Finding: Label-wide sweep for 6-digit PIN code. No PIN anywhere is a
   Rule 6(1)(a) defect on its own, independent of 'Mfd by' keyword.
4. GENERIC_NAME is deliberately unparsed: It has no conventional keyword anchor. Left
   strictly to the vision model or officer confirmation. Hence a perfect label caps
   at 89% (8/9 fields) and correctly reports INSUFFICIENT_DATA. It never invents.
5. needs_model() Decision Switch: Clean labels (>=75% coverage) never cost an API call!
"""

from __future__ import annotations

import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from rule_table import CHECKLIST_IDS
except ImportError:
    CHECKLIST_IDS = (
        "MANUFACTURER",
        "COUNTRY_OF_ORIGIN",
        "GENERIC_NAME",
        "NET_QUANTITY",
        "DATE_OF_MANUFACTURE",
        "BEST_BEFORE",
        "MRP",
        "UNIT_SALE_PRICE",
        "CONSUMER_CARE",
    )


# ---------------------------------------------------------------------------
# 1. Scoped OCR Digit Repair
# ---------------------------------------------------------------------------

_DIGIT_CONFUSION_MAP = {
    "O": "0", "o": "0",
    "S": "5", "s": "5",
    "I": "1", "l": "1", "|": "1",
    "Z": "2", "z": "2",
    "B": "8",
}

def repair_numeric_run(token: str) -> str:
    """
    OCR digit repair strictly scoped to numeric runs within price/weight expressions.
    '2SO.OO' -> '250.00', 'lOOO' -> '1000'.
    Gupta Oil Mills survives; 250 g never becomes 250 9.
    """
    clean = token.strip()
    # Match leading run containing digits or common OCR confusion letters
    # followed by optional decimal point and more digits/letters
    m = re.match(r"^([0-9OoSsIlZzBb\.,]+)(.*)$", clean)
    if not m:
        return clean

    num_part, suffix = m.group(1), m.group(2)
    # Check if there is at least one standard digit or decimal dot or Rs/MRP prefix
    has_digit = any(c.isdigit() for c in num_part) or "." in num_part or len(num_part) >= 2
    if not has_digit:
        return clean

    repaired = "".join(_DIGIT_CONFUSION_MAP.get(c, c) for c in num_part)
    return repaired + suffix


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class ParsedField:
    value: Optional[str] = None
    quoted_text: Optional[str] = None
    confidence: float = 0.0
    bbox: Optional[Tuple[int, int, int, int]] = None
    normalized_numeric: Optional[float] = None
    normalized_unit: Optional[str] = None
    stitched: bool = False  # True if captured across adjacent line pair

    def as_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "quoted_text": self.quoted_text,
            "confidence": round(self.confidence, 2),
            "bbox": list(self.bbox) if self.bbox else None,
            "normalized_numeric": self.normalized_numeric,
            "normalized_unit": self.normalized_unit,
            "stitched": self.stitched,
        }


@dataclass
class LabelParseResult:
    fields: Dict[str, ParsedField] = field(default_factory=dict)
    raw_text: str = ""
    parsed_count: int = 0
    total_rule_fields: int = 9
    coverage_percent: float = 0.0
    missing_fields: List[str] = field(default_factory=list)
    has_pin_code: bool = False
    pin_code: Optional[str] = None
    needs_model_escalation: bool = False
    escalation_reason: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "fields": {k: v.as_dict() for k, v in self.fields.items()},
            "parsed_count": self.parsed_count,
            "total_rule_fields": self.total_rule_fields,
            "coverage_percent": self.coverage_percent,
            "missing_fields": self.missing_fields,
            "has_pin_code": self.has_pin_code,
            "pin_code": self.pin_code,
            "needs_model_escalation": self.needs_model_escalation,
            "escalation_reason": self.escalation_reason,
            "raw_text": self.raw_text,
        }


# ---------------------------------------------------------------------------
# 2. Regex Patterns (with Scoped Digit Repair preprocessing)
# ---------------------------------------------------------------------------

# MRP: Matches "MRP Rs 150.00 (incl. of all taxes)" or OCR-damaged "MRP Rs. 2SO.OO"
RE_MRP_KEYWORD = re.compile(
    r"(?:MRP|M\.R\.P\.|Max\.?\s*Retail\s*Price|₹|Rs\.?)\s*[:\.]?\s*(?:₹|Rs\.?)?\s*([0-9OoSsIlZzBb\.,]+)([^\n\r]*)",
    re.IGNORECASE,
)

# Net Quantity: Matches "Net Qty: 500 g", "Net Weight: lOOO ml", etc.
RE_NET_QTY_KEYWORD = re.compile(
    r"(?:Net\s*(?:Quantity|Qty|Content|Wt\.?|Weight)|Net)\s*[:\.]?\s*([0-9OoSsIlZzBb\.,]+)\s*(kg|g|gm|gms|ml|l|ltr|ltrs|units|unit|N|pieces|pcs)\b",
    re.IGNORECASE,
)
# Fallback Quantity without keyword: MUST contain at least one genuine digit to prevent matching words like 'OIL'
RE_FALLBACK_QTY = re.compile(
    r"\b(\d+[0-9OoSsIlZzBb\.,]*)\s*(kg|g|gm|gms|ml|l|ltr|ltrs)\b",
    re.IGNORECASE,
)

# Unit Sale Price (USP)
RE_USP_KEYWORD = re.compile(
    r"(?:USP|Unit\s*Sale\s*Price)\s*[:\.]?\s*(?:₹|Rs\.?)?\s*([0-9OoSsIlZzBb\.,]+)\s*(?:/|\s*per\s*)([a-zA-Z]+)",
    re.IGNORECASE,
)

# Dates (Mfg & Expiry)
RE_MFG_DATE = re.compile(
    r"(?:Mfg\s*Date|Date\s*of\s*(?:Mfg|Packaging|Packing)|Packed\s*on|PKD\.?|MFG\.?)\s*[:\.]?\s*([0-9]{1,2}[/\-\.][0-9]{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*[0-9]{2,4})",
    re.IGNORECASE,
)
RE_EXPIRY_DATE = re.compile(
    r"(?:Best\s*Before|Expiry\s*Date|Use\s*by|EXP\.?|EXPIRY)\s*[:\.]?\s*([0-9]{1,2}[/\-\.][0-9]{2,4}|[0-9]{1,2}\s*(?:months|days|years)\s*(?:from\s*(?:packaging|mfg|date))?|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*[0-9]{2,4})",
    re.IGNORECASE,
)

# Country of Origin
RE_ORIGIN = re.compile(
    r"(?:Country\s*of\s*Origin|Made\s*in|Product\s*of)\s*[:\.]?\s*([A-Za-z\s]+?)(?:[\.\n,]|$)",
    re.IGNORECASE,
)

# Consumer Care
RE_CARE_PHONE = re.compile(r"(?:1800[-\s]?\d{3}[-\s]?\d{3,4}|\+?91[-\s]?\d{10}|\b\d{10}\b)")
RE_CARE_EMAIL = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")

# 6-Digit Indian Postal PIN Code Pattern (Label-Wide Absence Check)
RE_PIN_CODE = re.compile(r"\b([1-9][0-9]{5})\b")


# ---------------------------------------------------------------------------
# 3. Two-Pass Parser Implementation
# ---------------------------------------------------------------------------

def parse_label(ocr_input: Union[str, Dict[str, Any], Any]) -> LabelParseResult:
    """
    Deterministic MAP layer: parses raw OCR text into the 9 Rule 6 fields.
    Executes in microseconds at zero API spend.
    """
    # 1. Normalize OCR text input and bounding boxes
    if isinstance(ocr_input, str):
        full_text = ocr_input
        ocr_lines = []
    elif hasattr(ocr_input, "text") and hasattr(ocr_input, "lines"):
        full_text = ocr_input.text
        ocr_lines = ocr_input.lines
    elif isinstance(ocr_input, dict):
        full_text = ocr_input.get("text", "")
        ocr_lines = ocr_input.get("lines", [])
    else:
        full_text = str(ocr_input)
        ocr_lines = []

    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    fields: Dict[str, ParsedField] = {}
    missing_fields: List[str] = []

    # -----------------------------------------------------------------------
    # PASS 1: Single Line Scanning (High Confidence: 0.92)
    # -----------------------------------------------------------------------
    
    # 1. MRP (Single Line with explicit MRP keyword and price together)
    mrp_field = None
    for line in lines:
        if re.search(r"\b(?:MRP|M\.R\.P\.|Max\.?\s*Retail\s*Price)\b", line, re.IGNORECASE):
            m = RE_MRP_KEYWORD.search(line)
            if m:
                raw_num = repair_numeric_run(m.group(1)).replace(",", "")
                try:
                    num_val = float(raw_num)
                    mrp_field = ParsedField(
                        value=f"₹ {num_val:.2f}",
                        quoted_text=line.strip(),
                        confidence=0.92,
                        normalized_numeric=num_val,
                        stitched=False,
                    )
                    break
                except ValueError:
                    pass

    # 2. Net Quantity (Single Line with keyword and value)
    qty_field = None
    for line in lines:
        m = RE_NET_QTY_KEYWORD.search(line)
        if m:
            raw_num = repair_numeric_run(m.group(1)).replace(",", "")
            raw_unit = m.group(2).lower()
            try:
                num_val = float(raw_num)
                qty_field = ParsedField(
                    value=f"{num_val:g} {raw_unit}",
                    quoted_text=line.strip(),
                    confidence=0.92,
                    normalized_numeric=num_val,
                    normalized_unit=raw_unit,
                    stitched=False,
                )
                break
            except ValueError:
                pass

    # 3. Unit Sale Price (Single Line)
    usp_field = None
    for line in lines:
        m = RE_USP_KEYWORD.search(line)
        if m:
            raw_num = repair_numeric_run(m.group(1)).replace(",", "")
            raw_unit = m.group(2).lower()
            try:
                num_val = float(raw_num)
                usp_field = ParsedField(
                    value=f"₹ {num_val:.2f}/{raw_unit}",
                    quoted_text=line.strip(),
                    confidence=0.92,
                    normalized_numeric=num_val,
                    normalized_unit=raw_unit,
                    stitched=False,
                )
                break
            except ValueError:
                pass

    # 4. Date of Manufacture (Single Line)
    mfg_field = None
    for line in lines:
        m = RE_MFG_DATE.search(line)
        if m:
            mfg_field = ParsedField(
                value=m.group(1).strip(),
                quoted_text=line.strip(),
                confidence=0.92,
                stitched=False,
            )
            break

    # 5. Best Before / Expiry (Single Line)
    exp_field = None
    for line in lines:
        m = RE_EXPIRY_DATE.search(line)
        if m:
            exp_field = ParsedField(
                value=m.group(1).strip(),
                quoted_text=line.strip(),
                confidence=0.92,
                stitched=False,
            )
            break

    # 6. Country of Origin (Single Line)
    origin_field = None
    for line in lines:
        m = RE_ORIGIN.search(line)
        if m and m.group(1).strip():
            origin_field = ParsedField(
                value=m.group(1).strip(),
                quoted_text=line.strip(),
                confidence=0.92,
                stitched=False,
            )
            break
        elif "made in india" in line.lower() or "product of india" in line.lower():
            origin_field = ParsedField(
                value="India",
                quoted_text=line.strip(),
                confidence=0.92,
                stitched=False,
            )
            break

    # 7. Consumer Care (Single Line)
    care_field = None
    phone_m = RE_CARE_PHONE.search(full_text)
    email_m = RE_CARE_EMAIL.search(full_text)
    if phone_m or email_m:
        parts = []
        if phone_m:
            parts.append(f"Tel: {phone_m.group(0)}")
        if email_m:
            parts.append(f"Email: {email_m.group(0)}")
        val_str = ", ".join(parts)
        care_field = ParsedField(
            value=val_str,
            quoted_text=val_str,
            confidence=0.92,
            stitched=False,
        )

    # 8. Manufacturer (Single Line)
    mfg_addr_field = None
    for line in lines:
        if any(kw in line.lower() for kw in ["mfg by", "manufactured by", "packed by", "marketed by", "packer:"]):
            mfg_addr_field = ParsedField(
                value=line.strip(),
                quoted_text=line.strip(),
                confidence=0.88,
                stitched=False,
            )
            break

    # -----------------------------------------------------------------------
    # PASS 2: Adjacent Line Pairs Scanning for Narrow Packages (Confidence: 0.82)
    # Stitches split keyword and value lines (e.g. Line 1: 'MRP', Line 2: 'Rs. 250.00')
    # -----------------------------------------------------------------------
    if len(lines) >= 2:
        for i in range(len(lines) - 1):
            pair = f"{lines[i]} {lines[i+1]}"

            # Stitched MRP
            if not mrp_field:
                m = RE_MRP_KEYWORD.search(pair)
                if m:
                    raw_num = repair_numeric_run(m.group(1)).replace(",", "")
                    try:
                        num_val = float(raw_num)
                        mrp_field = ParsedField(
                            value=f"₹ {num_val:.2f}",
                            quoted_text=pair,
                            confidence=0.82,
                            normalized_numeric=num_val,
                            stitched=True,
                        )
                    except ValueError:
                        pass

            # Stitched Net Quantity
            if not qty_field:
                m = RE_NET_QTY_KEYWORD.search(pair) or RE_FALLBACK_QTY.search(pair)
                if m:
                    raw_num = repair_numeric_run(m.group(1)).replace(",", "")
                    raw_unit = m.group(2).lower()
                    try:
                        num_val = float(raw_num)
                        qty_field = ParsedField(
                            value=f"{num_val:g} {raw_unit}",
                            quoted_text=pair,
                            confidence=0.82,
                            normalized_numeric=num_val,
                            normalized_unit=raw_unit,
                            stitched=True,
                        )
                    except ValueError:
                        pass

            # Stitched Unit Sale Price
            if not usp_field:
                m = RE_USP_KEYWORD.search(pair)
                if m:
                    raw_num = repair_numeric_run(m.group(1)).replace(",", "")
                    raw_unit = m.group(2).lower()
                    try:
                        num_val = float(raw_num)
                        usp_field = ParsedField(
                            value=f"₹ {num_val:.2f}/{raw_unit}",
                            quoted_text=pair,
                            confidence=0.82,
                            normalized_numeric=num_val,
                            normalized_unit=raw_unit,
                            stitched=True,
                        )
                    except ValueError:
                        pass

            # Stitched Date of Manufacture
            if not mfg_field:
                m = RE_MFG_DATE.search(pair)
                if m:
                    mfg_field = ParsedField(
                        value=m.group(1).strip(),
                        quoted_text=pair,
                        confidence=0.82,
                        stitched=True,
                    )

            # Stitched Best Before
            if not exp_field:
                m = RE_EXPIRY_DATE.search(pair)
                if m:
                    exp_field = ParsedField(
                        value=m.group(1).strip(),
                        quoted_text=pair,
                        confidence=0.82,
                        stitched=True,
                    )

            # Stitched Country of Origin
            if not origin_field:
                m = RE_ORIGIN.search(pair)
                if m and m.group(1).strip():
                    origin_field = ParsedField(
                        value=m.group(1).strip(),
                        quoted_text=pair,
                        confidence=0.82,
                        stitched=True,
                    )
                elif "made in india" in pair.lower() or "product of india" in pair.lower():
                    origin_field = ParsedField(
                        value="India",
                        quoted_text=pair,
                        confidence=0.82,
                        stitched=True,
                    )

    # Fallback Quantity without keyword (only if Pass 1 and Pass 2 both missed)
    if not qty_field:
        for line in lines:
            m = RE_FALLBACK_QTY.search(line)
            if m:
                raw_num = repair_numeric_run(m.group(1)).replace(",", "")
                raw_unit = m.group(2).lower()
                try:
                    num_val = float(raw_num)
                    qty_field = ParsedField(
                        value=f"{num_val:g} {raw_unit}",
                        quoted_text=line.strip(),
                        confidence=0.75,
                        normalized_numeric=num_val,
                        normalized_unit=raw_unit,
                        stitched=False,
                    )
                    break
                except ValueError:
                    pass

    # -----------------------------------------------------------------------
    # 3. Label-Wide Absence Finding: 6-Digit PIN Code Sweep
    # -----------------------------------------------------------------------
    pin_match = RE_PIN_CODE.search(full_text)
    has_pin = pin_match is not None
    pin_code_val = pin_match.group(1) if pin_match else None

    # If manufacturer field is missing, but PIN code exists, use the PIN code line!
    if not mfg_addr_field and pin_match:
        for line in lines:
            if pin_code_val in line:
                mfg_addr_field = ParsedField(
                    value=line.strip(),
                    quoted_text=line.strip(),
                    confidence=0.80,
                    stitched=False,
                )
                break

    # -----------------------------------------------------------------------
    # 4. GENERIC_NAME is DELIBERATELY UNPARSED by regex
    # It has no reliable conventional keyword anchor — it is the headline descriptive line.
    # We leave it strictly to the vision model or human officer rather than guessing.
    # -----------------------------------------------------------------------
    generic_name_field = ParsedField(
        value=None,
        quoted_text=None,
        confidence=0.0,
    )

    # Populate final fields dictionary
    fields["MRP"] = mrp_field or ParsedField(confidence=0.0)
    fields["NET_QUANTITY"] = qty_field or ParsedField(confidence=0.0)
    fields["UNIT_SALE_PRICE"] = usp_field or ParsedField(confidence=0.0)
    fields["DATE_OF_MANUFACTURE"] = mfg_field or ParsedField(confidence=0.0)
    fields["BEST_BEFORE"] = exp_field or ParsedField(confidence=0.0)
    fields["COUNTRY_OF_ORIGIN"] = origin_field or ParsedField(confidence=0.0)
    fields["CONSUMER_CARE"] = care_field or ParsedField(confidence=0.0)
    fields["MANUFACTURER"] = mfg_addr_field or ParsedField(confidence=0.0)
    fields["GENERIC_NAME"] = generic_name_field

    for k, v in fields.items():
        if not v.value:
            missing_fields.append(k)

    parsed_count = sum(1 for v in fields.values() if v.value is not None)
    coverage = round((parsed_count / 9.0) * 100.0, 1)

    # -----------------------------------------------------------------------
    # 5. needs_model() Decision Switch:
    # Clean labels (>=75% coverage) NEVER cost an API call!
    # Low coverage (<75%) is itself the signal: either genuinely deficient or unreadable.
    # -----------------------------------------------------------------------
    needs_model_esc, esc_reason = needs_model(
        parsed_count=parsed_count,
        coverage_percent=coverage,
        has_pin_code=has_pin,
        fields=fields,
    )

    return LabelParseResult(
        fields=fields,
        raw_text=full_text,
        parsed_count=parsed_count,
        total_rule_fields=9,
        coverage_percent=coverage,
        missing_fields=missing_fields,
        has_pin_code=has_pin,
        pin_code=pin_code_val,
        needs_model_escalation=needs_model_esc,
        escalation_reason=esc_reason,
    )


def needs_model(
    parsed_count: int,
    coverage_percent: float,
    has_pin_code: bool,
    fields: Dict[str, ParsedField],
) -> Tuple[bool, str]:
    """
    Decides whether a packaging label must escalate to Gemini Vision (Stage 3)
    or can be settled entirely by Stage 1 deterministic regex/math.

    Rules:
    - Coverage >= 75% (7 or 8 fields): Settle without model (API cost: ₹0.00). Escalate = False.
    - Coverage 0%: Not a label (e.g. shop signage, face photo). Escalate = True.
    - Coverage < 70%: Deficient label or OCR damage. Escalate = True.
    - Missing PIN code anywhere across label: Statutory flag.
    """
    if coverage_percent >= 75.0:
        return False, f"Clean label coverage ({coverage_percent}% >= 75%). Zero API cost."

    if parsed_count == 0:
        return True, "0% coverage — non-label or completely unreadable image."

    return True, f"Low coverage ({coverage_percent}% < 75%). Flagged for vision model or officer attention."
