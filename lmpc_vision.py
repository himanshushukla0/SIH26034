#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — LMPC VISION MODULE
 Aliases and exposes the computer vision, label gate, and barcode decoding pipeline.
"""
from __future__ import annotations
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from image_gate import *
