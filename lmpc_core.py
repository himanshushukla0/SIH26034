#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — CORE CONSTANTS & STATUS CALCULATIONS
"""

from __future__ import annotations
from typing import Any, Dict, Sequence

PASS = "PASS"
FAIL = "FAIL"
UNVERIFIED = "UNVERIFIED"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
COMPLIANT = "COMPLIANT"
NON_COMPLIANT = "NON_COMPLIANT"
PARTIAL_VIOLATION = "PARTIAL_VIOLATION"
NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"

SRC_NONE = "NONE"
SRC_LABEL = "LABEL"
SRC_BARCODE = "BARCODE"
SRC_DATABASE = "DATABASE"

UNVERIFIED_TEXT = "(unverified — not readable in image)"


def counts(checks: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Count passed, failed, and unverified checks."""
    total = len(checks)
    passed = sum(1 for c in checks if c.get("status") == PASS)
    failed = sum(1 for c in checks if c.get("status") == FAIL)
    unverified = sum(1 for c in checks if c.get("status") in (UNVERIFIED, "UNVERIFIED", "REVIEW"))
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "unverified": unverified,
    }


def overall_status(checks: Sequence[Dict[str, Any]]) -> str:
    """Calculate overall statutory compliance verdict."""
    c = counts(checks)
    if c["total"] == 0:
        return INSUFFICIENT_DATA
    if c["unverified"] > 0:
        return INSUFFICIENT_DATA
    if c["failed"] > 0:
        return NON_COMPLIANT
    if c["passed"] == c["total"]:
        return COMPLIANT
    return INSUFFICIENT_DATA
