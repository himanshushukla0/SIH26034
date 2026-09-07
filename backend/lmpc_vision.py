#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — LMPC VISION MODULE (BACKEND EXPORT)
"""
from __future__ import annotations
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from image_gate import *
