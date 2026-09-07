#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — CORE ALIAS (backend)
"""
from __future__ import annotations
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from lmpc_core import (
    PASS,
    FAIL,
    UNVERIFIED,
    INSUFFICIENT_DATA,
    COMPLIANT,
    NON_COMPLIANT,
    PARTIAL_VIOLATION,
    NEEDS_MANUAL_REVIEW,
    SRC_NONE,
    SRC_LABEL,
    SRC_BARCODE,
    SRC_DATABASE,
    UNVERIFIED_TEXT,
    counts,
    overall_status,
)
