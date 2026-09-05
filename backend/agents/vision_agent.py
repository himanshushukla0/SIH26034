"""
SIH26034 — Agent 2: Computer Vision & Multimodal OCR Agent

Uses Google Gemini 3.6 Flash multimodal vision to extract all 10
mandatory LMPC declarations from packaging images in a single
zero-shot inference call with structured JSON output.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, Optional

from google import genai
from google.genai import types as genai_types

from backend.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured extraction schema — defines what Gemini must return
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are an expert Indian Legal Metrology compliance inspector.
Analyze this product packaging image and extract ALL mandatory declarations
required under the Legal Metrology (Packaged Commodities) Rules, 2011.

For EACH field below, extract the value if visible, or return null if not found.
Also provide a confidence score (0.0 to 1.0) for each extraction.

Return a JSON object with this EXACT structure:
{
  "product_name": {"value": "...", "confidence": 0.95},
  "manufacturer_name": {"value": "...", "confidence": 0.90},
  "manufacturer_address": {"value": "...", "confidence": 0.85},
  "country_of_origin": {"value": "...", "confidence": 0.92},
  "generic_name": {"value": "...", "confidence": 0.88},
  "net_quantity": {"value": "500 g", "confidence": 0.95},
  "net_quantity_unit": {"value": "g", "confidence": 0.95},
  "net_quantity_value": {"value": 500, "confidence": 0.95},
  "manufacture_date": {"value": "03/2025", "confidence": 0.80},
  "expiry_date": {"value": "03/2026", "confidence": 0.85},
  "best_before": {"value": "12 months from packaging", "confidence": 0.80},
  "mrp": {"value": "150.00", "confidence": 0.97},
  "mrp_includes_taxes": {"value": true, "confidence": 0.90},
  "unit_sale_price": {"value": "0.30 per g", "confidence": 0.75},
  "consumer_care_name": {"value": "...", "confidence": 0.70},
  "consumer_care_phone": {"value": "...", "confidence": 0.70},
  "consumer_care_email": {"value": "...", "confidence": 0.65},
  "consumer_care_address": {"value": "...", "confidence": 0.60},
  "barcode_number": {"value": "8901234567890", "confidence": 0.92},
  "is_imported": {"value": false, "confidence": 0.85},
  "importer_name": {"value": null, "confidence": 0.0},
  "importer_address": {"value": null, "confidence": 0.0},
  "additional_declarations": ["FSSAI Lic No: ...", "Veg/Non-Veg symbol"],
  "detected_languages": ["English", "Hindi"],
  "packaging_type": "box|bottle|can|pouch|sachet|tube|jar|other",
  "label_readability": "clear|partially_obscured|blurry|damaged"
}

IMPORTANT RULES:
- For MRP: Extract ONLY the numeric value in Indian Rupees (₹ or Rs.).
- For Net Quantity: Separate the numeric value and unit. Use ONLY legal SI units:
  g, kg, ml, l, cm, m, units. Do NOT use gms, kilos, ltr, mL etc.
- For dates: Use MM/YYYY format if month and year are visible.
- For Unit Sale Price (USP): Extract if printed. Format as "X.XX per unit".
- If a field is not visible or not applicable, set value to null and confidence to 0.0.
- If text is in Hindi or regional language, translate to English in the value field.
- Report ALL text you can see, even partially obscured text.

Return ONLY valid JSON. No markdown, no explanation, no code fences."""


class VisionAgent:
    """
    Extracts mandatory LMPC declarations from product packaging images
    using Google Gemini 3.6 Flash multimodal vision.
    """

    def __init__(self) -> None:
        self.client = genai.Client()
        self.model = settings.GEMINI_MODEL
        logger.info("VisionAgent initialized with model: %s", self.model)

    async def extract_from_image(
        self,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
    ) -> dict[str, Any]:
        """
        Extract all mandatory declarations from a packaging image.

        Args:
            image_path: Path to the image file on disk.
            image_bytes: Raw image bytes (from upload).

        Returns:
            Dictionary containing extracted declarations with confidence scores.

        Raises:
            ValueError: If neither image_path nor image_bytes is provided.
            RuntimeError: If Gemini API call fails.
        """
        if image_path is None and image_bytes is None:
            raise ValueError("Provide either image_path or image_bytes.")

        # Load image bytes
        if image_bytes is None:
            image_bytes = Path(image_path).read_bytes()

        # Detect MIME type from magic bytes
        mime_type = self._detect_mime_type(image_bytes)

        logger.info(
            "Processing image (%d bytes, %s) with %s",
            len(image_bytes),
            mime_type,
            self.model,
        )

        try:
            # Build multimodal content
            image_part = genai_types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=[EXTRACTION_PROMPT, image_part],
                config=genai_types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for factual extraction
                    max_output_tokens=4096,
                ),
            )

            # Parse the JSON response
            raw_text = response.text.strip()

            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text[: raw_text.rfind("```")]
                raw_text = raw_text.strip()

            extractions = json.loads(raw_text)
            logger.info(
                "Successfully extracted %d fields from packaging image.",
                len(extractions),
            )
            return extractions

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini response as JSON: %s", e)
            logger.debug("Raw response: %s", raw_text)
            raise RuntimeError(
                f"Gemini returned invalid JSON. Raw response: {raw_text[:500]}"
            ) from e
        except Exception as e:
            logger.error("Gemini API call failed: %s", e)
            raise RuntimeError(f"Vision extraction failed: {e}") from e

    @staticmethod
    def _detect_mime_type(data: bytes) -> str:
        """Detect image MIME type from magic bytes."""
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if data[:2] == b"\xff\xd8":
            return "image/jpeg"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if data[:3] == b"GIF":
            return "image/gif"
        # Default to JPEG
        return "image/jpeg"


# Module-level singleton
vision_agent = VisionAgent()
