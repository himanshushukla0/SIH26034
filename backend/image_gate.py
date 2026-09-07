#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — IMAGE GATE & BARCODE DECODER (BACKEND EXPORT)
"""
from __future__ import annotations
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from image_gate import (
    OK,
    NOT_A_LABEL,
    CONTAINS_PERSON,
    TOO_BLURRY,
    TOO_SMALL,
    UNREADABLE_FILE,
    MIN_EDGE_LENGTH_PX,
    BLUR_LAPLACIAN_MIN,
    MIN_TEXT_LINES,
    MIN_EDGE_DENSITY,
    NO_BARCODE,
    BARCODE_UNREADABLE,
    BARCODE_OK,
    ImageAssessment,
    DecodedBarcode,
    assess_image,
    decode_barcodes,
    barcode_status,
    prepare_audit_input,
)
