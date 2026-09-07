#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — RULE & PENALTY TABLE (BACKEND PACKAGE EXPORT)

 Re-exports from root rule_table.py or provides the complete standalone rule table
 for direct backend imports.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure root directory is accessible if rule_table is imported at root
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from rule_table import (
        RULE_TABLE_VERSION,
        RULE_TABLE_VERIFIED_AGAINST,
        IMPROVEMENT_NOTICE,
        CIVIL_PENALTY,
        CRIMINAL_FINE,
        CRITICAL,
        MAJOR,
        MINOR,
        Consequence,
        PenaltyLadder,
        Rule,
        RULES,
        BY_ID,
        CHECKLIST_IDS,
        LADDER_36_1,
        LADDER_36_2,
        LADDER_29,
        MPE_TABLE,
        MPE_SOURCE_NOTE,
        rule,
        consequence_for,
        notice_kind_for,
        max_permissible_error,
    )
except ImportError:
    # Fallback in isolated container environments where only /app/backend is copied
    from dataclasses import dataclass
    from typing import Dict, List, Optional, Tuple

    RULE_TABLE_VERSION = "2026.09-janvishwas2026"
    RULE_TABLE_VERIFIED_AGAINST = (
        "Legal Metrology Act, 2009 (India Code text as on 07-05-2026, incorporating the "
        "Jan Vishwas (Amendment of Provisions) Act, 2026, in force 01-05-2026); "
        "Legal Metrology (Packaged Commodities) Rules, 2011 as amended to date.")

    IMPROVEMENT_NOTICE = "IMPROVEMENT_NOTICE"
    CIVIL_PENALTY = "CIVIL_PENALTY"
    CRIMINAL_FINE = "CRIMINAL_FINE"

    CRITICAL, MAJOR, MINOR = "CRITICAL", "MAJOR", "MINOR"

    @dataclass(frozen=True)
    class Consequence:
        kind: str
        min_inr: Optional[int] = None
        max_inr: Optional[int] = None
        imprisonment_months: Optional[int] = None
        note: str = ""

        def describe(self) -> str:
            if self.kind == IMPROVEMENT_NOTICE:
                return ("Warning with an improvement notice under section 15(6). "
                        "No monetary penalty for a first contravention.")
            money = ""
            if self.min_inr is not None and self.max_inr is not None:
                money = f"Rs {self.min_inr:,} to Rs {self.max_inr:,}"
            elif self.max_inr is not None:
                money = f"up to Rs {self.max_inr:,}"
            label = "Penalty" if self.kind == CIVIL_PENALTY else "Fine"
            out = f"{label} {money}".strip()
            if self.imprisonment_months:
                out += f", or imprisonment up to {self.imprisonment_months} months, or both"
            return out + ("  " + self.note if self.note else "")

    @dataclass(frozen=True)
    class PenaltyLadder:
        section: str
        first: Consequence
        second: Consequence
        subsequent: Consequence

        def at(self, offence_number: int) -> Consequence:
            if offence_number <= 1:
                return self.first
            if offence_number == 2:
                return self.second
            return self.subsequent

    LADDER_36_1 = PenaltyLadder(
        section="Section 36(1), Legal Metrology Act, 2009",
        first=Consequence(IMPROVEMENT_NOTICE),
        second=Consequence(CIVIL_PENALTY, max_inr=500_000),
        subsequent=Consequence(CRIMINAL_FINE, min_inr=2_500_000, max_inr=5_000_000),
    )

    LADDER_36_2 = PenaltyLadder(
        section="Section 36(2), Legal Metrology Act, 2009",
        first=Consequence(CRIMINAL_FINE, min_inr=10_000, max_inr=100_000),
        second=Consequence(CRIMINAL_FINE, max_inr=500_000),
        subsequent=Consequence(CRIMINAL_FINE, max_inr=5_000_000, imprisonment_months=12),
    )

    LADDER_29 = PenaltyLadder(
        section="Section 29, Legal Metrology Act, 2009",
        first=Consequence(IMPROVEMENT_NOTICE),
        second=Consequence(CIVIL_PENALTY, max_inr=50_000),
        subsequent=Consequence(CRIMINAL_FINE, min_inr=100_000, max_inr=200_000),
    )

    @dataclass(frozen=True)
    class Rule:
        id: str
        citation: str
        subject: str
        requirement: str
        obligation_section: str
        ladder: PenaltyLadder
        severity: str
        applies_to: str = "all pre-packaged commodities"
        remedy: str = ""
        amendment_note: str = ""

    RULES: Tuple[Rule, ...] = (
        Rule(
            id="MANUFACTURER",
            citation="Rule 6(1)(a), Legal Metrology (Packaged Commodities) Rules, 2011",
            subject="Name & complete address of manufacturer / packer / importer",
            requirement=(
                "The package must bear the name and complete address of the manufacturer, or "
                "of the packer where the manufacturer is not the packer, or of the importer "
                "for an imported commodity. A complete address includes the PIN code."),
            obligation_section="Section 18(1), Legal Metrology Act, 2009",
            ladder=LADDER_36_1, severity=MAJOR,
            remedy=("Print the full name and complete postal address, including PIN code, of "
                    "the manufacturer / packer / importer on the principal display panel."),
        ),
        Rule(
            id="COUNTRY_OF_ORIGIN",
            citation="Rule 6(1)(aa), Legal Metrology (Packaged Commodities) Rules, 2011",
            subject="Country of origin",
            requirement=("An imported pre-packaged commodity must declare the country of "
                         "origin or manufacture or assembly."),
            obligation_section="Section 18(1), Legal Metrology Act, 2009",
            ladder=LADDER_36_1, severity=MAJOR,
            applies_to="imported commodities; and all listings under Rule 6(10)",
            remedy="Declare the country of origin on the principal display panel.",
        ),
        Rule(
            id="GENERIC_NAME",
            citation="Rule 6(1)(b), Legal Metrology (Packaged Commodities) Rules, 2011",
            subject="Common or generic name of the commodity",
            requirement=("The package must declare the common or generic name of the "
                         "commodity contained in it; where the package contains more than one "
                         "product, the name and quantity of each."),
            obligation_section="Section 18(1), Legal Metrology Act, 2009",
            ladder=LADDER_36_1, severity=MINOR,
            remedy="Declare the common or generic name of the commodity.",
        ),
        Rule(
            id="NET_QUANTITY",
            citation="Rule 6(1)(c), Legal Metrology (Packaged Commodities) Rules, 2011",
            subject="Net quantity in standard units",
            requirement=(
                "The package must declare the net quantity, in terms of the standard unit of "
                "weight or measure, or in number where sold by number. Standard symbols only "
                "(g, kg, ml, l, m, cm) — abbreviations such as 'gms', 'ltr' or 'Kgs' are not "
                "standard units."),
            obligation_section="Section 18(1), Legal Metrology Act, 2009",
            ladder=LADDER_36_1, severity=MAJOR,
            remedy=("Declare the net quantity using the standard unit symbol prescribed under "
                    "the Act (g, kg, ml, l)."),
        ),
        Rule(
            id="NET_QUANTITY_UNIT_FORMAT",
            citation="Rule 6(1)(c) read with section 11(1)(d), Legal Metrology Act, 2009",
            subject="Non-standard unit symbol used for net quantity",
            requirement=("No person shall quote or indicate a quantity otherwise than in "
                         "accordance with the standard unit of weight or measure. 'gms', "
                         "'ltr', 'Kgs', 'mgs' are not standard symbols."),
            obligation_section="Section 11(1)(d), Legal Metrology Act, 2009",
            ladder=LADDER_29, severity=MAJOR,
            remedy="Replace the non-standard abbreviation with the prescribed unit symbol.",
        ),
        Rule(
            id="NET_QUANTITY_SHORTFALL",
            citation=("Rule 6(1)(c) read with the First Schedule (Rule 2(e)) — "
                      "maximum permissible error"),
            subject="Net quantity less than declared, beyond permissible error",
            requirement=("The actual net quantity in the package must not fall short of the "
                         "declared quantity by more than the maximum permissible error in the "
                         "First Schedule."),
            obligation_section="Section 18(2), Legal Metrology Act, 2009",
            ladder=LADDER_36_2, severity=CRITICAL,
            remedy=("Correct the filling process so that net content meets the declared "
                    "quantity within the permissible error, and withdraw affected stock."),
            amendment_note=("Short measure remains a criminal offence after Jan Vishwas 2026 — "
                            "it was not converted to a civil penalty."),
        ),
        Rule(
            id="DATE_OF_MANUFACTURE",
            citation="Rule 6(1)(d), Legal Metrology (Packaged Commodities) Rules, 2011",
            subject="Month & year of manufacture / packing / import",
            requirement=("The package must declare the month and the year in which the "
                         "commodity was manufactured, pre-packed or imported."),
            obligation_section="Section 18(1), Legal Metrology Act, 2009",
            ladder=LADDER_36_1, severity=MAJOR,
            remedy="Print the month and year of manufacture / packing / import.",
        ),
        Rule(
            id="BEST_BEFORE",
            citation="Rule 6(1)(da), Legal Metrology (Packaged Commodities) Rules, 2011",
            subject="Best before / use by date",
            requirement=("Where applicable, the package must declare the 'best before' or "
                         "'use by' date, month and year."),
            obligation_section="Section 18(1), Legal Metrology Act, 2009",
            ladder=LADDER_36_1, severity=CRITICAL,
            applies_to="food, cosmetics, pharmaceuticals and other perishable commodities",
            remedy="Print the best before / use by date on the principal display panel.",
            amendment_note=("The backend currently cites this as 'Rule 6(1)(da) / Rule 6(1)(e)'. "
                            "6(1)(e) is retail sale price — drop it from this citation."),
        ),
        Rule(
            id="MRP",
            citation="Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
            subject="Retail sale price (MRP)",
            requirement=("The retail sale price must be declared in the form 'Maximum Retail "
                         "Price Rs ____ inclusive of all taxes'. For an imported commodity the "
                         "price must be in Indian rupees."),
            obligation_section="Section 18(1), Legal Metrology Act, 2009",
            ladder=LADDER_36_1, severity=MAJOR,
            remedy="Declare the MRP in rupees with the words 'inclusive of all taxes'.",
        ),
        Rule(
            id="UNIT_SALE_PRICE",
            citation=("Rule 6(11), Legal Metrology (Packaged Commodities) Rules, 2011 "
                      "(inserted by the Legal Metrology (Packaged Commodities) Second "
                      "Amendment Rules, 2021, G.S.R. 779(E))"),
            subject="Unit sale price",
            requirement=("The unit sale price must be declared, rounded off to the nearest "
                         "rupee or paise, in the prescribed form (per gram / kilogram / "
                         "millilitre / litre / centimetre / metre / number, as the commodity "
                         "requires)."),
            obligation_section="Section 18(1), Legal Metrology Act, 2009",
            ladder=LADDER_36_1, severity=MAJOR,
            remedy="Declare the unit sale price alongside the MRP in the prescribed form.",
        ),
        Rule(
            id="CONSUMER_CARE",
            citation="Rule 6(1)(n), Legal Metrology (Packaged Commodities) Rules, 2011",
            subject="Consumer care details",
            requirement=("The package must declare the name, designation, complete address, "
                         "telephone number and email address of the person who can be "
                         "contacted for consumer complaints."),
            obligation_section="Section 18(1), Legal Metrology Act, 2009",
            ladder=LADDER_36_1, severity=MAJOR,
            remedy=("Print the consumer care contact name/designation, address, telephone "
                    "number and email address."),
        ),
    )

    BY_ID: Dict[str, Rule] = {r.id: r for r in RULES}

    CHECKLIST_IDS: Tuple[str, ...] = (
        "MANUFACTURER", "COUNTRY_OF_ORIGIN", "GENERIC_NAME", "NET_QUANTITY",
        "DATE_OF_MANUFACTURE", "BEST_BEFORE", "MRP", "UNIT_SALE_PRICE", "CONSUMER_CARE",
    )

    def rule(rule_id: str) -> Rule:
        try:
            return BY_ID[rule_id]
        except KeyError:
            raise KeyError(f"Unknown rule id {rule_id!r}. Known: {sorted(BY_ID)}") from None

    def consequence_for(rule_id: str, offence_number: int = 1) -> Consequence:
        return rule(rule_id).ladder.at(offence_number)

    def notice_kind_for(rule_ids: List[str], offence_number: int = 1) -> str:
        kinds = {consequence_for(rid, offence_number).kind for rid in rule_ids}
        if kinds and kinds == {IMPROVEMENT_NOTICE}:
            return IMPROVEMENT_NOTICE
        return "SHOW_CAUSE"

    MPE_TABLE: Tuple[Tuple[float, bool, float], ...] = (
        (50,           True,  9.0),
        (100,          False, 4.5),
        (200,          True,  4.5),
        (300,          False, 9.0),
        (500,          True,  3.0),
        (1000,         False, 15.0),
        (10000,        True,  1.5),
        (15000,        False, 150.0),
        (float("inf"), True,  1.0),
    )

    MPE_SOURCE_NOTE = (
        "First Schedule (Rule 2(e)), LMPC Rules 2011. Note: the backend currently cites the "
        "'Second Schedule' for net quantity — the Second Schedule is not the permissible "
        "error table.")

    def max_permissible_error(declared_qty: float) -> Tuple[float, str]:
        if declared_qty <= 0:
            raise ValueError("Declared quantity must be positive.")
        for upper, is_pct, value in MPE_TABLE:
            if declared_qty <= upper:
                if is_pct:
                    return declared_qty * value / 100.0, f"{value}% of declared quantity"
                return value, f"{value} g/ml (fixed allowance for this band)"
        raise AssertionError("unreachable — MPE table has an infinite final band")
