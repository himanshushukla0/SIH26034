#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — RULE & PENALTY TABLE ALIAS (lmpc_rules)
 Re-exports rule_table as lmpc_rules for notice drafting and auditing.
"""

from __future__ import annotations
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from backend import rule_table
    from backend.rule_table import *
except ImportError:
    import rule_table
    from rule_table import *
