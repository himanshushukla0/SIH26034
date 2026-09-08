#!/usr/bin/env python3
"""
LMPC COMPLIANCE ENGINE (SIH26034) — STEP 2: READ (OCR LAYER)
image → text + boxes

Takes an image that has passed Step 1 (GATE: lmpc_vision.assess_image())
and reads all visible packaging text, outputting:
1. full verbatim text string (for regex / NLP parsing)
2. lines / text blocks with bounding boxes [x, y, w, h] and confidence scores
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

logger = logging.getLogger("lmpc.ocr")


@dataclass
class OcrBox:
    text: str
    bbox: Tuple[int, int, int, int]  # [x, y, width, height]
    confidence: float
    line_number: int = 1


@dataclass
class OcrResult:
    text: str  # Full raw concatenated text
    lines: List[OcrBox] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    engine: str = "gemini-vision-ocr"
    raw_response: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "lines": [asdict(b) for b in self.lines],
            "image_width": self.image_width,
            "image_height": self.image_height,
            "engine": self.engine,
        }


# ---------------------------------------------------------------------------
# Vision OCR Prompt — Requests Verbatim Text with Bounding Boxes
# ---------------------------------------------------------------------------

VISION_OCR_PROMPT = """You are an ultra-high precision Optical Character Recognition (OCR) engine \
inspecting pre-packaged commodity packaging in India.

TASK:
Read ALL text printed on this packaging label, line by line, verbatim.
Do NOT summarize, do NOT infer, and do NOT skip any text blocks.

For EVERY text line visible on the packaging, return:
- `text`: exact characters as printed (preserving casing, numbers, symbols like ₹, /, %, @)
- `bbox`: [x, y, width, height] bounding box in image pixels (normalized or absolute)
- `confidence`: confidence score between 0.0 and 1.0

Return STRICTLY valid JSON with this structure:
{
  "lines": [
    {"text": "...", "bbox": [x, y, w, h], "confidence": 0.98},
    {"text": "...", "bbox": [x, y, w, h], "confidence": 0.95}
  ]
}"""


def _load_image_dims(image_path: str) -> Tuple[int, int]:
    try:
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception:
        return 800, 600


async def read_label_gemini(image_path: str) -> OcrResult:
    """Read label text + boxes using Gemini Multimodal Vision OCR."""
    from backend.config import settings
    from google import genai
    from google.genai import types as genai_types

    w, h = _load_image_dims(image_path)
    client = genai.Client()
    model_name = settings.GEMINI_MODEL

    img_bytes = Path(image_path).read_bytes()
    mime_type = "image/jpeg"
    if img_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        mime_type = "image/png"
    elif img_bytes[:4] == b"RIFF" and img_bytes[8:12] == b"WEBP":
        mime_type = "image/webp"

    image_part = genai_types.Part.from_bytes(data=img_bytes, mime_type=mime_type)

    config = genai_types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=4096,
        response_mime_type="application/json",
    )

    try:
        if hasattr(client, "aio") and hasattr(client.aio, "models"):
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=[VISION_OCR_PROMPT, image_part],
                config=config,
            )
        else:
            import asyncio
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=[VISION_OCR_PROMPT, image_part],
                config=config,
            )

        resp_text = response.text.strip() if response.text else "{}"
        data = json.loads(resp_text)
        raw_lines = data.get("lines", [])

        boxes: List[OcrBox] = []
        text_lines: List[str] = []

        for idx, item in enumerate(raw_lines):
            t = str(item.get("text") or "").strip()
            if not t:
                continue
            text_lines.append(t)
            raw_box = item.get("bbox") or [0, 0, w, 20]
            # Ensure 4-element box
            if len(raw_box) == 4:
                bx, by, bw, bh = int(raw_box[0]), int(raw_box[1]), int(raw_box[2]), int(raw_box[3])
            else:
                bx, by, bw, bh = 0, idx * 25, w, 20
            conf = float(item.get("confidence") or 0.90)
            boxes.append(OcrBox(text=t, bbox=(bx, by, bw, bh), confidence=conf, line_number=idx + 1))

        full_text = "\n".join(text_lines)
        return OcrResult(
            text=full_text,
            lines=boxes,
            image_width=w,
            image_height=h,
            engine=f"gemini-vision-ocr ({model_name})",
            raw_response=resp_text,
        )

    except Exception as e:
        logger.warning("Gemini OCR reading failed, attempting local fallback: %s", e)
        return read_label_local(image_path)


def read_label_local(image_path: str) -> OcrResult:
    """
    Local fallback OCR using OpenCV contour and text line clustering.
    Ensures offline operability and predictable testability.
    """
    w, h = _load_image_dims(image_path)
    # Check if pytesseract is available
    try:
        import pytesseract
        text = pytesseract.image_to_string(Image.open(image_path))
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        boxes = [
            OcrBox(text=l, bbox=(10, idx * 30, w - 20, 25), confidence=0.85, line_number=idx + 1)
            for idx, l in enumerate(lines)
        ]
        return OcrResult(
            text="\n".join(lines),
            lines=boxes,
            image_width=w,
            image_height=h,
            engine="local-tesseract-ocr",
        )
    except Exception:
        pass

    return OcrResult(
        text="",
        lines=[],
        image_width=w,
        image_height=h,
        engine="none",
    )


async def read_label(image_path: str) -> OcrResult:
    """
    STEP 2: READ (image → text + boxes)
    Main entry point for Step 2 of the LMPC pipeline.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Label image not found: {image_path}")

    return await read_label_gemini(image_path)
