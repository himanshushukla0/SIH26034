#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — NOTICE DRAFTING (BACKEND EXPORT)
 Re-exports lmpc_notice from root or provides direct access.
"""

from __future__ import annotations
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from lmpc_notice import (
        DEFAULT_COMPLIANCE_DAYS,
        DEFAULT_SHOW_CAUSE_DAYS,
        DISCLAIMER,
        evidence_fingerprint,
        select_instrument,
        draft_improvement_notice,
        draft_show_cause_notice,
        draft_notice,
    )
except ImportError:
    pass
