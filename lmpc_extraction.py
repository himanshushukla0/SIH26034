#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — VISION EXTRACTION CONTRACT

 The contract:
   1. Every field defaults to null. The model must QUOTE the text it read, verbatim.
   2. Every field carries its own confidence and a bounding box.
   3. The model gets an explicit escape hatch — is_product_label: false — and is told
      that using it is the correct answer, not a failure.
   4. The response is VALIDATED here. A field whose quoted text is absent, or whose
      confidence is below threshold, is downgraded to UNVERIFIED before it is shown.
   5. Nothing that came back at low confidence can produce a COMPLIANT verdict.

 No API client here — feed it whatever your backend gets back from Gemini. Pure
 validation, so it is testable without a key.
"""

from __future__ import annotations
import json, logging, os, re, sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    import lmpc_core as core
except ImportError:
    from backend import lmpc_core as core

try:
    import lmpc_rules as rules
except ImportError:
    from backend import lmpc_rules as rules

log = logging.getLogger("lmpc.extraction")

MIN_FIELD_CONFIDENCE = 0.70   # below this, a field is shown as unverified, not as fact
MIN_MEAN_CONFIDENCE = 0.55    # below this, the whole extraction is rejected

FIELD_KEYS: Tuple[str, ...] = rules.CHECKLIST_IDS


EXTRACTION_PROMPT = """You are reading a photograph for an Indian Legal Metrology \
compliance check under the Legal Metrology (Packaged Commodities) Rules, 2011.

FIRST, decide what this photograph actually shows.

If it is NOT a photograph of a pre-packaged commodity's label — if it shows a person, a \
place, an animal, a screen, a document, or anything else — you MUST return:

{"is_product_label": false, "what_it_shows": "<a short factual description>", "fields": {}}

Returning is_product_label: false is a CORRECT and expected answer. It is not a failure. \
Do not attempt to extract declarations from an image that is not a label.

If it IS a product label, extract ONLY what you can actually read in the image.

ABSOLUTE RULES:
- If a declaration is not visible in this image, set its value to null. Never infer it, \
never recall it from your knowledge of the brand, never supply a typical value.
- `quoted_text` must be the characters as they appear on the package, verbatim, \
including case and punctuation. If you cannot quote it, the value must be null.
- `confidence` is your confidence that you READ THIS CORRECTLY FROM THIS IMAGE, not your \
confidence about what such a product usually declares.
- `bbox` is [x, y, width, height] in pixels for the region you read it from.
- Knowing the brand is not the same as reading the label. If you recognise the product \
but cannot read a field, that field is null.

Return strictly this JSON and nothing else:

{
  "is_product_label": true,
  "what_it_shows": "<short description>",
  "commodity_type": "<e.g. packaged food, cosmetic, or null>",
  "fields": {
    "MANUFACTURER":        {"value": null, "quoted_text": null, "confidence": 0.0, "bbox": null},
    "COUNTRY_OF_ORIGIN":   {"value": null, "quoted_text": null, "confidence": 0.0, "bbox": null},
    "GENERIC_NAME":        {"value": null, "quoted_text": null, "confidence": 0.0, "bbox": null},
    "NET_QUANTITY":        {"value": null, "quoted_text": null, "confidence": 0.0, "bbox": null},
    "DATE_OF_MANUFACTURE": {"value": null, "quoted_text": null, "confidence": 0.0, "bbox": null},
    "BEST_BEFORE":         {"value": null, "quoted_text": null, "confidence": 0.0, "bbox": null},
    "MRP":                 {"value": null, "quoted_text": null, "confidence": 0.0, "bbox": null},
    "UNIT_SALE_PRICE":     {"value": null, "quoted_text": null, "confidence": 0.0, "bbox": null},
    "CONSUMER_CARE":       {"value": null, "quoted_text": null, "confidence": 0.0, "bbox": null}
  }
}"""


RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["is_product_label", "fields"],
    "properties": {
        "is_product_label": {"type": "boolean"},
        "what_it_shows": {"type": "string"},
        "commodity_type": {"type": ["string", "null"]},
        "fields": {"type": "object", "properties": {
            k: {"type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "quoted_text": {"type": ["string", "null"]},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "bbox": {"type": ["array", "null"], "items": {"type": "number"},
                             "minItems": 4, "maxItems": 4}},
                "required": ["value", "quoted_text", "confidence"]} for k in FIELD_KEYS}},
    },
}


REJECTED_NOT_LABEL = "REJECTED_NOT_A_LABEL"
REJECTED_LOW_CONFIDENCE = "REJECTED_LOW_CONFIDENCE"
REJECTED_MALFORMED = "REJECTED_MALFORMED_RESPONSE"
ACCEPTED = "ACCEPTED"


@dataclass
class ExtractionResult:
    status: str
    message: str
    checks: List[Dict[str, Any]] = field(default_factory=list)
    what_it_shows: str = ""
    mean_confidence: Optional[float] = None
    downgraded: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.status == ACCEPTED

    def audit_status(self) -> str:
        return core.INSUFFICIENT_DATA if not self.accepted else core.overall_status(self.checks)


def _coerce(payload: Any) -> Optional[Dict[str, Any]]:
    """Models wrap JSON in prose and code fences. Recover it, or give up cleanly."""
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return None
    text = payload.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def validate_extraction(model_response: Any,
                        min_field_confidence: float = MIN_FIELD_CONFIDENCE,
                        min_mean_confidence: float = MIN_MEAN_CONFIDENCE) -> ExtractionResult:
    """
    Turn a raw model response into a checklist that can be trusted, or into a refusal.
    There is no path here that produces a confident verdict from a doubtful reading.
    """
    data = _coerce(model_response)
    if data is None:
        return ExtractionResult(REJECTED_MALFORMED,
            "The vision model did not return usable JSON. No audit has been recorded.",
            raw={"response": str(model_response)[:2000]})

    if not isinstance(data.get("fields"), dict):
        return ExtractionResult(REJECTED_MALFORMED,
            "The vision model's response did not contain a 'fields' object. "
            "No audit has been recorded.", raw=data)

    shows = str(data.get("what_it_shows") or "").strip()

    if data.get("is_product_label") is not True:
        return ExtractionResult(REJECTED_NOT_LABEL,
            ("The image was not identified as a pre-packaged commodity label"
             + (f" — it appears to show {shows}." if shows else ".")
             + " No compliance audit has been performed and no verdict recorded."),
            what_it_shows=shows, raw=data)

    checks: List[Dict[str, Any]] = []
    downgraded: List[str] = []
    confidences: List[float] = []

    for key in FIELD_KEYS:
        rule = rules.rule(key)
        raw_field = data["fields"].get(key) or {}
        value = raw_field.get("value")
        quoted = raw_field.get("quoted_text")
        try:
            conf = float(raw_field.get("confidence") or 0.0)
        except (TypeError, ValueError):
            conf = 0.0
        conf = max(0.0, min(1.0, conf))

        entry: Dict[str, Any] = {
            "clause": rule.citation.split(",")[0], "rule_id": key, "label": rule.subject,
            "confidence": round(conf, 2), "bbox": raw_field.get("bbox"),
            "quoted_text": quoted}

        if value in (None, "", "null", "N/A"):
            entry.update({"val": core.UNVERIFIED_TEXT, "status": core.UNVERIFIED,
                          "source": core.SRC_NONE})
            checks.append(entry)
            continue

        # Claimed a value but could not quote it -> recalled, not read. Reject it.
        if not quoted or not str(quoted).strip():
            downgraded.append(f"{key} (value given with no quoted text — not read from the image)")
            entry.update({"val": f"Model reported '{value}' but could not quote it from "
                                 f"the image — treated as unverified",
                          "status": core.UNVERIFIED, "source": core.SRC_NONE})
            checks.append(entry)
            continue

        confidences.append(conf)

        if conf < min_field_confidence:
            downgraded.append(f"{key} (confidence {conf:.2f} below {min_field_confidence:.2f})")
            entry.update({"val": f"'{value}' read at low confidence ({conf:.0%}) — officer "
                                 f"confirmation required",
                          "status": core.UNVERIFIED, "source": core.SRC_NONE})
            checks.append(entry)
            continue

        entry.update({"val": str(value), "status": core.PASS, "source": core.SRC_LABEL})
        checks.append(entry)

    mean_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

    if not confidences or mean_conf < min_mean_confidence:
        return ExtractionResult(REJECTED_LOW_CONFIDENCE,
            (f"The label could not be read reliably (mean confidence {mean_conf:.0%}, "
             f"minimum {min_mean_confidence:.0%}). No verdict has been recorded — "
             f"retake the photograph of the declaration panel."),
            checks=[], what_it_shows=shows, mean_confidence=mean_conf,
            downgraded=downgraded, raw=data)

    return ExtractionResult(ACCEPTED,
        "Label read. Fields below carry the confidence at which each was read.",
        checks=checks, what_it_shows=shows, mean_confidence=mean_conf,
        downgraded=downgraded, raw=data)


def compliance_summary(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Report counts, not a single percentage.

    The screenshot said "98% COMPLIANCE / 10 checks / 10 passed". 10 of 10 is 100%, so
    the 98% was not computed from the checks at all. A score that does not follow from
    the findings is worse than no score: it looks quantitative and is not.
    """
    c = core.counts(checks)
    verified_total = c["passed"] + c["failed"]
    return {
        "total_checks": c["total"], "passed": c["passed"], "failed": c["failed"],
        "unverified": c["unverified"], "verdict": core.overall_status(checks),
        "score_percent": (round(100.0 * c["passed"] / verified_total, 1)
                          if verified_total == c["total"] and c["total"] else None),
        "score_note": ("Score is withheld until every declaration has been determined. "
                       f"{c['unverified']} of {c['total']} are still unverified."
                       if c["unverified"] else "All declarations determined."),
    }


def build_audit(image_gate: Dict[str, Any], extraction: ExtractionResult,
                barcode_text: Optional[str] = None) -> Dict[str, Any]:
    """
    What your FastAPI endpoint should return. It cannot produce a COMPLIANT verdict
    unless every field was read from the image, quoted, and above the confidence floor.
    """
    if not image_gate.get("proceed"):
        return {"audit_recorded": False, "verdict": None,
                "reason": image_gate.get("user_message"),
                "guidance": image_gate.get("guidance"),
                "image": image_gate.get("image"), "checks": [], "summary": None}

    if not extraction.accepted:
        return {"audit_recorded": False, "verdict": None, "reason": extraction.message,
                "guidance": "Retake the photograph of the declaration panel and try again.",
                "image": image_gate.get("image"), "barcode": image_gate.get("barcode"),
                "what_it_shows": extraction.what_it_shows, "checks": [], "summary": None}

    summary = compliance_summary(extraction.checks)
    return {"audit_recorded": True, "verdict": summary["verdict"],
            "reason": extraction.message, "image": image_gate.get("image"),
            "barcode": image_gate.get("barcode"), "barcode_text": barcode_text,
            "what_it_shows": extraction.what_it_shows,
            "mean_confidence": extraction.mean_confidence,
            "downgraded_fields": extraction.downgraded,
            "checks": extraction.checks, "summary": summary}
