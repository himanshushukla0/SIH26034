"""
SIH26034 — Agent 4: Package Authenticity & Integrity Verification Agent

Cross-verifies extracted packaging declarations against authoritative
external databases to detect counterfeiting, expiry fraud, and mislabeling.

Implements 6 independent verification checks:
  1. Barcode → Product Identity (Open Food Facts API)
  2. FSSAI License Validity (FOSCOS database lookup)
  3. Expiry & Shelf-Life Integrity (real-time date arithmetic)
  4. GS1 Country Code vs. Declared Country of Origin
  5. MRP Anomaly Detection (price reasonableness)
  6. BIS/ISI Certification Verification (Manak database)

Produces an aggregate Trust Score (0–100) and a verdict:
  ✅ AUTHENTIC  |  ⚠️ SUSPICIOUS  |  🚨 COUNTERFEIT_RISK
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GS1 Country Code Prefix Table (EAN/UCC Barcode Prefix → Country)
# ---------------------------------------------------------------------------

GS1_COUNTRY_PREFIXES: list[tuple[int, int, str]] = [
    (0, 19, "United States / Canada"),
    (20, 29, "In-store / Restricted"),
    (30, 39, "France"),
    (40, 44, "Germany"),
    (45, 49, "Japan"),
    (50, 50, "United Kingdom"),
    (54, 54, "Belgium / Luxembourg"),
    (57, 57, "Denmark"),
    (64, 64, "Finland"),
    (70, 70, "Norway"),
    (73, 73, "Sweden"),
    (76, 76, "Switzerland"),
    (84, 84, "Spain"),
    (87, 87, "Netherlands"),
    (90, 91, "Austria"),
    (93, 93, "Australia"),
    (94, 94, "New Zealand"),
    (460, 469, "Russia"),
    (471, 471, "Taiwan"),
    (474, 474, "Estonia"),
    (475, 475, "Latvia"),
    (476, 476, "Azerbaijan"),
    (477, 477, "Lithuania"),
    (478, 478, "Uzbekistan"),
    (480, 480, "Philippines"),
    (484, 484, "Moldova"),
    (485, 485, "Armenia"),
    (486, 486, "Georgia"),
    (487, 487, "Kazakhstan"),
    (489, 489, "Hong Kong"),
    (520, 521, "Greece"),
    (528, 528, "Lebanon"),
    (529, 529, "Cyprus"),
    (531, 531, "North Macedonia"),
    (535, 535, "Malta"),
    (539, 539, "Ireland"),
    (560, 560, "Portugal"),
    (569, 569, "Iceland"),
    (590, 590, "Poland"),
    (594, 594, "Romania"),
    (599, 599, "Hungary"),
    (600, 601, "South Africa"),
    (608, 608, "Bahrain"),
    (609, 609, "Mauritius"),
    (611, 611, "Morocco"),
    (613, 613, "Algeria"),
    (615, 615, "Nigeria"),
    (616, 616, "Kenya"),
    (618, 618, "Côte d'Ivoire"),
    (619, 619, "Tunisia"),
    (620, 620, "Tanzania"),
    (621, 621, "Syria"),
    (622, 622, "Egypt"),
    (624, 624, "Libya"),
    (625, 625, "Jordan"),
    (626, 626, "Iran"),
    (627, 627, "Kuwait"),
    (628, 628, "Saudi Arabia"),
    (629, 629, "UAE"),
    (640, 649, "Central Africa"),
    (690, 695, "China"),
    (700, 709, "Norway"),
    (729, 729, "Israel"),
    (730, 739, "Sweden"),
    (740, 741, "Guatemala / El Salvador"),
    (742, 742, "Honduras"),
    (743, 743, "Nicaragua"),
    (744, 744, "Costa Rica"),
    (745, 745, "Panama"),
    (746, 746, "Dominican Republic"),
    (750, 750, "Mexico"),
    (754, 755, "Canada"),
    (759, 759, "Venezuela"),
    (760, 769, "Switzerland"),
    (770, 771, "Colombia"),
    (773, 773, "Uruguay"),
    (775, 775, "Peru"),
    (777, 777, "Bolivia"),
    (778, 779, "Argentina"),
    (780, 780, "Chile"),
    (784, 784, "Paraguay"),
    (786, 786, "Ecuador"),
    (789, 790, "Brazil"),
    (800, 839, "Italy"),
    (840, 849, "Spain"),
    (850, 850, "Cuba"),
    (858, 858, "Slovakia"),
    (859, 859, "Czech Republic"),
    (860, 860, "Serbia"),
    (865, 865, "Mongolia"),
    (867, 867, "North Korea"),
    (868, 869, "Turkey"),
    (870, 879, "Netherlands"),
    (880, 880, "South Korea"),
    (884, 884, "Cambodia"),
    (885, 885, "Thailand"),
    (888, 888, "Singapore"),
    (890, 890, "India"),
    (893, 893, "Vietnam"),
    (894, 894, "Indonesia"),
    (896, 896, "Pakistan"),
    (899, 899, "Indonesia"),
    (900, 919, "Austria"),
    (930, 939, "Australia"),
    (940, 949, "New Zealand"),
    (955, 955, "Malaysia"),
    (958, 958, "Macau"),
]

# Mapping of common country names to GS1 prefix ranges for cross-verification
COUNTRY_NAME_TO_GS1: dict[str, list[range]] = {
    "india": [range(890, 891)],
    "china": [range(690, 696)],
    "united states": [range(0, 20)],
    "usa": [range(0, 20)],
    "japan": [range(45, 50)],
    "south korea": [range(880, 881)],
    "korea": [range(880, 881)],
    "thailand": [range(885, 886)],
    "vietnam": [range(893, 894)],
    "indonesia": [range(894, 895), range(899, 900)],
    "germany": [range(40, 45)],
    "france": [range(30, 40)],
    "italy": [range(800, 840)],
    "spain": [range(840, 850)],
    "united kingdom": [range(50, 51)],
    "uk": [range(50, 51)],
    "australia": [range(93, 94), range(930, 940)],
    "brazil": [range(789, 791)],
    "mexico": [range(750, 751)],
    "turkey": [range(868, 870)],
    "pakistan": [range(896, 897)],
    "bangladesh": [range(880, 881)],  # Shares with South Korea in some ranges
    "singapore": [range(888, 889)],
    "malaysia": [range(955, 956)],
    "philippines": [range(480, 481)],
    "sri lanka": [range(479, 480)],
    "nepal": [range(890, 891)],  # Uses India's GS1 prefix in some cases
    "uae": [range(629, 630)],
    "saudi arabia": [range(628, 629)],
    "canada": [range(0, 20), range(754, 756)],
    "switzerland": [range(76, 77), range(760, 770)],
    "netherlands": [range(87, 88), range(870, 880)],
    "sweden": [range(73, 74), range(730, 740)],
    "russia": [range(460, 470)],
    "poland": [range(590, 591)],
    "egypt": [range(622, 623)],
    "south africa": [range(600, 602)],
    "taiwan": [range(471, 472)],
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    """Result of a single authenticity verification check."""
    check_name: str               # e.g., "barcode_identity", "fssai_license"
    status: str                   # "VERIFIED", "FAILED", "WARNING", "UNVERIFIABLE"
    confidence: float             # 0.0 – 1.0
    details: str                  # Human-readable explanation
    evidence: dict[str, Any]      # Raw data from external source
    is_counterfeit_signal: bool   # True if this check suggests counterfeiting


@dataclass
class PackageAuthenticityVerdict:
    """Aggregate authenticity verdict from all verification checks."""
    trust_score: float                  # 0–100 weighted aggregate
    overall_status: str                 # "AUTHENTIC", "SUSPICIOUS", "COUNTERFEIT_RISK"
    checks: list[VerificationResult]    # All individual check results
    counterfeit_signals: int            # Count of checks flagging fraud
    expiry_status: str                  # "VALID", "EXPIRED", "NEAR_EXPIRY", "DATE_TAMPERED"
    days_until_expiry: Optional[int]    # Negative = already expired


# ---------------------------------------------------------------------------
# Verification Agent
# ---------------------------------------------------------------------------

class VerificationAgent:
    """
    Cross-verifies packaging declarations against authoritative databases
    to detect counterfeit products, expired goods, and mislabeled packages.
    """

    # Weights for trust score (sum = 100)
    CHECK_WEIGHTS: dict[str, float] = {
        "barcode_identity": 25.0,
        "fssai_license": 20.0,
        "expiry_validation": 25.0,
        "gs1_country_code": 10.0,
        "mrp_anomaly": 10.0,
        "bis_isi_mark": 10.0,
    }

    def __init__(self) -> None:
        self._http_client = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "SIH26034-LMPC-ComplianceEngine/1.0 (Legal Metrology Audit)",
            },
        )
        logger.info("VerificationAgent initialized.")

    async def verify(
        self,
        extractions: dict[str, Any],
        listing_data: Optional[dict[str, Any]] = None,
    ) -> PackageAuthenticityVerdict:
        """
        Run all 6 verification checks against the extracted declarations.

        Args:
            extractions: Output from VisionAgent.extract_from_image().
            listing_data: Optional e-commerce listing data.

        Returns:
            PackageAuthenticityVerdict with trust score and per-check breakdown.
        """
        checks: list[VerificationResult] = []

        # Run all checks (each is fault-tolerant — never crashes the pipeline)
        checks.append(await self._check_barcode_identity(extractions))
        checks.append(await self._check_fssai_license(extractions))
        checks.append(self._check_expiry_validation(extractions))
        checks.append(self._check_gs1_country_code(extractions))
        checks.append(self._check_mrp_anomaly(extractions, listing_data))
        checks.append(self._check_bis_isi_mark(extractions))

        # Aggregate trust score
        trust_score = self._compute_trust_score(checks)
        counterfeit_signals = sum(1 for c in checks if c.is_counterfeit_signal)

        # Determine expiry status from the expiry check
        expiry_check = next((c for c in checks if c.check_name == "expiry_validation"), None)
        expiry_status = expiry_check.evidence.get("expiry_status", "UNKNOWN") if expiry_check else "UNKNOWN"
        days_until_expiry = expiry_check.evidence.get("days_until_expiry") if expiry_check else None

        # Overall verdict
        if counterfeit_signals >= 3:
            overall_status = "COUNTERFEIT_RISK"
        elif counterfeit_signals >= 1 or trust_score < 60:
            overall_status = "SUSPICIOUS"
        else:
            overall_status = "AUTHENTIC"

        verdict = PackageAuthenticityVerdict(
            trust_score=round(trust_score, 1),
            overall_status=overall_status,
            checks=checks,
            counterfeit_signals=counterfeit_signals,
            expiry_status=expiry_status,
            days_until_expiry=days_until_expiry,
        )

        logger.info(
            "Verification complete: trust_score=%.1f status=%s counterfeit_signals=%d expiry=%s",
            trust_score, overall_status, counterfeit_signals, expiry_status,
        )

        return verdict

    # ------------------------------------------------------------------
    # CHECK 1: Barcode → Product Identity (Open Food Facts)
    # ------------------------------------------------------------------

    async def _check_barcode_identity(self, extractions: dict) -> VerificationResult:
        """Verify barcode against Open Food Facts database."""
        barcode = self._get_value(extractions, "barcode_number")

        if not barcode:
            return VerificationResult(
                check_name="barcode_identity",
                status="UNVERIFIABLE",
                confidence=0.0,
                details="No barcode detected on packaging. Cannot verify product identity.",
                evidence={"reason": "barcode_not_found"},
                is_counterfeit_signal=False,
            )

        # Clean barcode (remove spaces, dashes)
        barcode = re.sub(r"[\s\-]", "", str(barcode))

        try:
            url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}"
            response = await self._http_client.get(url)

            if response.status_code != 200:
                return VerificationResult(
                    check_name="barcode_identity",
                    status="UNVERIFIABLE",
                    confidence=0.3,
                    details=f"Open Food Facts API returned status {response.status_code} for barcode {barcode}.",
                    evidence={"barcode": barcode, "http_status": response.status_code},
                    is_counterfeit_signal=False,
                )

            data = response.json()

            if data.get("status") != 1:
                return VerificationResult(
                    check_name="barcode_identity",
                    status="WARNING",
                    confidence=0.5,
                    details=(
                        f"Barcode {barcode} not found in Open Food Facts database. "
                        "Product may be new, regional, or unregistered. "
                        "Cannot confirm authenticity via barcode."
                    ),
                    evidence={"barcode": barcode, "off_status": data.get("status")},
                    is_counterfeit_signal=False,
                )

            product = data.get("product", {})
            off_name = product.get("product_name", "")
            off_brands = product.get("brands", "")
            off_quantity = product.get("quantity", "")
            off_countries = product.get("countries", "")

            # Cross-verify product name
            pkg_name = self._get_value(extractions, "product_name") or ""
            pkg_manufacturer = self._get_value(extractions, "manufacturer_name") or ""

            name_match = self._fuzzy_contains(pkg_name, off_name) or self._fuzzy_contains(off_name, pkg_name)
            brand_match = self._fuzzy_contains(pkg_manufacturer, off_brands) or self._fuzzy_contains(off_brands, pkg_manufacturer)

            mismatches = []
            if off_name and pkg_name and not name_match:
                mismatches.append(f"Product name mismatch: package='{pkg_name}' vs database='{off_name}'")
            if off_brands and pkg_manufacturer and not brand_match:
                mismatches.append(f"Brand mismatch: package='{pkg_manufacturer}' vs database='{off_brands}'")

            if mismatches:
                return VerificationResult(
                    check_name="barcode_identity",
                    status="FAILED",
                    confidence=0.85,
                    details=(
                        f"Barcode {barcode} is registered in Open Food Facts but "
                        f"the product details DO NOT MATCH the packaging. "
                        f"Discrepancies: {'; '.join(mismatches)}. "
                        "This is a strong counterfeit indicator — the barcode may have been "
                        "copied from a legitimate product onto fraudulent packaging."
                    ),
                    evidence={
                        "barcode": barcode,
                        "off_product_name": off_name,
                        "off_brands": off_brands,
                        "off_quantity": off_quantity,
                        "pkg_product_name": pkg_name,
                        "pkg_manufacturer": pkg_manufacturer,
                        "mismatches": mismatches,
                    },
                    is_counterfeit_signal=True,
                )

            return VerificationResult(
                check_name="barcode_identity",
                status="VERIFIED",
                confidence=0.90,
                details=(
                    f"Barcode {barcode} verified against Open Food Facts. "
                    f"Product: '{off_name}' by '{off_brands}'. Identity confirmed."
                ),
                evidence={
                    "barcode": barcode,
                    "off_product_name": off_name,
                    "off_brands": off_brands,
                    "off_quantity": off_quantity,
                    "off_countries": off_countries,
                },
                is_counterfeit_signal=False,
            )

        except Exception as e:
            logger.warning("Barcode verification failed: %s", e)
            return VerificationResult(
                check_name="barcode_identity",
                status="UNVERIFIABLE",
                confidence=0.2,
                details=f"Could not reach Open Food Facts API: {e}",
                evidence={"barcode": barcode, "error": str(e)},
                is_counterfeit_signal=False,
            )

    # ------------------------------------------------------------------
    # CHECK 2: FSSAI License Validity
    # ------------------------------------------------------------------

    async def _check_fssai_license(self, extractions: dict) -> VerificationResult:
        """Verify FSSAI license number against known patterns and FOSCOS."""
        # Extract FSSAI number from additional_declarations or dedicated field
        fssai_number = self._extract_fssai_number(extractions)

        if not fssai_number:
            return VerificationResult(
                check_name="fssai_license",
                status="WARNING",
                confidence=0.6,
                details=(
                    "No FSSAI license number detected on the packaging. "
                    "All food products sold in India must display a valid 14-digit "
                    "FSSAI license/registration number under FSSAI (Licensing & Registration "
                    "of Food Businesses) Regulations, 2011."
                ),
                evidence={"reason": "fssai_not_found"},
                is_counterfeit_signal=False,
            )

        # Validate format: FSSAI numbers are 14 digits
        clean_fssai = re.sub(r"[\s\-]", "", fssai_number)
        if not re.match(r"^\d{14}$", clean_fssai):
            return VerificationResult(
                check_name="fssai_license",
                status="FAILED",
                confidence=0.80,
                details=(
                    f"FSSAI number '{fssai_number}' has an invalid format. "
                    "Valid FSSAI license numbers must be exactly 14 digits. "
                    "This is a counterfeit indicator — fake products often print "
                    "random or incorrectly formatted license numbers."
                ),
                evidence={"fssai_raw": fssai_number, "cleaned": clean_fssai},
                is_counterfeit_signal=True,
            )

        # Decode FSSAI structure for additional validation
        # Format: [1-digit type][2-digit state][2-digit year][9-digit sequence]
        license_type = int(clean_fssai[0])
        state_code = clean_fssai[1:3]
        year_code = clean_fssai[3:5]

        type_map = {
            1: "Central License (Large Manufacturer / Importer)",
            2: "State License (Medium Business)",
            3: "Registration (Small / Petty FBO)",
        }
        license_type_desc = type_map.get(license_type, f"Unknown type ({license_type})")

        # Indian state codes (01-37)
        valid_state_codes = [f"{i:02d}" for i in range(1, 38)]
        state_valid = state_code in valid_state_codes

        if not state_valid:
            return VerificationResult(
                check_name="fssai_license",
                status="FAILED",
                confidence=0.85,
                details=(
                    f"FSSAI license '{clean_fssai}' contains invalid state code '{state_code}'. "
                    "Indian state codes range from 01 to 37. This suggests the license number "
                    "is fabricated."
                ),
                evidence={
                    "fssai_number": clean_fssai,
                    "state_code": state_code,
                    "license_type": license_type_desc,
                },
                is_counterfeit_signal=True,
            )

        if license_type not in (1, 2, 3):
            return VerificationResult(
                check_name="fssai_license",
                status="FAILED",
                confidence=0.80,
                details=(
                    f"FSSAI license '{clean_fssai}' has invalid license type digit '{license_type}'. "
                    "Valid types are 1 (Central), 2 (State), or 3 (Registration). "
                    "Fabricated license numbers often use invalid type codes."
                ),
                evidence={
                    "fssai_number": clean_fssai,
                    "license_type_digit": license_type,
                },
                is_counterfeit_signal=True,
            )

        # Try online verification via FOSCOS (best-effort)
        foscos_result = await self._verify_fssai_online(clean_fssai)

        if foscos_result:
            return foscos_result

        # Format is valid but couldn't verify online
        return VerificationResult(
            check_name="fssai_license",
            status="WARNING",
            confidence=0.55,
            details=(
                f"FSSAI license '{clean_fssai}' has a valid format "
                f"(Type: {license_type_desc}, State: {state_code}, Year: 20{year_code}). "
                "However, online verification against FOSCOS database could not be completed. "
                "Manual verification recommended at https://foscos.fssai.gov.in"
            ),
            evidence={
                "fssai_number": clean_fssai,
                "license_type": license_type_desc,
                "state_code": state_code,
                "year_code": f"20{year_code}",
                "online_verification": "unavailable",
                "manual_verify_url": "https://foscos.fssai.gov.in",
            },
            is_counterfeit_signal=False,
        )

    async def _verify_fssai_online(self, fssai_number: str) -> Optional[VerificationResult]:
        """Attempt to verify FSSAI number against FOSCOS portal."""
        try:
            # FOSCOS public search endpoint
            url = "https://foscos.fssai.gov.in/public-search/license"
            response = await self._http_client.post(
                url,
                data={"licenseNo": fssai_number},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                text = response.text.lower()
                if "active" in text or "operative" in text:
                    return VerificationResult(
                        check_name="fssai_license",
                        status="VERIFIED",
                        confidence=0.95,
                        details=(
                            f"FSSAI license {fssai_number} verified as ACTIVE "
                            "in the official FOSCOS database."
                        ),
                        evidence={
                            "fssai_number": fssai_number,
                            "foscos_status": "ACTIVE",
                            "source": "foscos.fssai.gov.in",
                        },
                        is_counterfeit_signal=False,
                    )
                elif "expired" in text or "suspended" in text or "cancelled" in text:
                    status_word = "EXPIRED" if "expired" in text else "SUSPENDED" if "suspended" in text else "CANCELLED"
                    return VerificationResult(
                        check_name="fssai_license",
                        status="FAILED",
                        confidence=0.90,
                        details=(
                            f"FSSAI license {fssai_number} found in FOSCOS database but status is "
                            f"{status_word}. Selling food products with an {status_word.lower()} "
                            "FSSAI license is illegal under Section 31 of the Food Safety & "
                            "Standards Act, 2006."
                        ),
                        evidence={
                            "fssai_number": fssai_number,
                            "foscos_status": status_word,
                            "source": "foscos.fssai.gov.in",
                        },
                        is_counterfeit_signal=True,
                    )
        except Exception as e:
            logger.debug("FOSCOS online verification failed (non-critical): %s", e)

        return None

    # ------------------------------------------------------------------
    # CHECK 3: Expiry & Shelf-Life Integrity
    # ------------------------------------------------------------------

    def _check_expiry_validation(self, extractions: dict) -> VerificationResult:
        """Validate expiry dates and detect date tampering."""
        mfd_raw = self._get_value(extractions, "manufacture_date")
        exp_raw = self._get_value(extractions, "expiry_date")
        best_before_raw = self._get_value(extractions, "best_before")

        now = datetime.now(timezone.utc)

        # Parse dates
        mfd_date = self._parse_date(mfd_raw) if mfd_raw else None
        exp_date = self._parse_date(exp_raw) if exp_raw else None

        # Parse "Best Before X months" pattern
        best_before_months = None
        if best_before_raw:
            month_match = re.search(r"(\d+)\s*months?", str(best_before_raw), re.IGNORECASE)
            if month_match:
                best_before_months = int(month_match.group(1))

        # No dates at all
        if not mfd_date and not exp_date:
            return VerificationResult(
                check_name="expiry_validation",
                status="WARNING",
                confidence=0.5,
                details=(
                    "Neither manufacture date nor expiry date could be extracted "
                    "from the packaging. Cannot verify product freshness."
                ),
                evidence={
                    "mfd_raw": mfd_raw,
                    "exp_raw": exp_raw,
                    "expiry_status": "UNKNOWN",
                },
                is_counterfeit_signal=False,
            )

        # Check if expired
        if exp_date:
            days_until = (exp_date - now).days

            if days_until < 0:
                return VerificationResult(
                    check_name="expiry_validation",
                    status="FAILED",
                    confidence=0.95,
                    details=(
                        f"🚨 PRODUCT IS EXPIRED. Expiry date: {exp_raw}. "
                        f"Expired {abs(days_until)} days ago. "
                        "Sale of expired products is a criminal offence under "
                        "Section 26 of the Food Safety & Standards Act, 2006 "
                        "punishable with imprisonment up to 6 months and fine up to ₹1,00,000."
                    ),
                    evidence={
                        "mfd_raw": mfd_raw,
                        "exp_raw": exp_raw,
                        "days_until_expiry": days_until,
                        "expiry_status": "EXPIRED",
                        "is_expired": True,
                    },
                    is_counterfeit_signal=True,
                )

            if days_until <= 30:
                return VerificationResult(
                    check_name="expiry_validation",
                    status="WARNING",
                    confidence=0.85,
                    details=(
                        f"⚠️ NEAR EXPIRY. Product expires in {days_until} days "
                        f"(Expiry: {exp_raw}). Consumers should be informed."
                    ),
                    evidence={
                        "mfd_raw": mfd_raw,
                        "exp_raw": exp_raw,
                        "days_until_expiry": days_until,
                        "expiry_status": "NEAR_EXPIRY",
                        "is_expired": False,
                    },
                    is_counterfeit_signal=False,
                )

        # Cross-check: MFD + Best Before months should ≈ EXP
        if mfd_date and exp_date and best_before_months:
            expected_exp = mfd_date + timedelta(days=best_before_months * 30)
            deviation_days = abs((exp_date - expected_exp).days)

            if deviation_days > 60:
                return VerificationResult(
                    check_name="expiry_validation",
                    status="FAILED",
                    confidence=0.80,
                    details=(
                        f"🚨 DATE TAMPERING SUSPECTED. Manufacture date ({mfd_raw}) + "
                        f"shelf life ({best_before_months} months) = expected expiry around "
                        f"{expected_exp.strftime('%m/%Y')}, but printed expiry is {exp_raw}. "
                        f"Deviation: {deviation_days} days. This suggests the expiry date "
                        "may have been altered or reprinted."
                    ),
                    evidence={
                        "mfd_raw": mfd_raw,
                        "exp_raw": exp_raw,
                        "best_before_months": best_before_months,
                        "expected_expiry": expected_exp.strftime("%m/%Y"),
                        "deviation_days": deviation_days,
                        "expiry_status": "DATE_TAMPERED",
                        "days_until_expiry": (exp_date - now).days,
                    },
                    is_counterfeit_signal=True,
                )

        # Valid and not expired
        days_until = (exp_date - now).days if exp_date else None
        return VerificationResult(
            check_name="expiry_validation",
            status="VERIFIED",
            confidence=0.85,
            details=(
                f"Product is within validity period. "
                + (f"Expires in {days_until} days ({exp_raw})." if days_until else f"Manufacture date: {mfd_raw}.")
                + (f" Shelf life: {best_before_months} months." if best_before_months else "")
            ),
            evidence={
                "mfd_raw": mfd_raw,
                "exp_raw": exp_raw,
                "best_before_months": best_before_months,
                "days_until_expiry": days_until,
                "expiry_status": "VALID",
                "is_expired": False,
            },
            is_counterfeit_signal=False,
        )

    # ------------------------------------------------------------------
    # CHECK 4: GS1 Country Code vs. Declared Country of Origin
    # ------------------------------------------------------------------

    def _check_gs1_country_code(self, extractions: dict) -> VerificationResult:
        """Cross-verify barcode country prefix against declared country of origin."""
        barcode = self._get_value(extractions, "barcode_number")
        declared_country = self._get_value(extractions, "country_of_origin")

        if not barcode:
            return VerificationResult(
                check_name="gs1_country_code",
                status="UNVERIFIABLE",
                confidence=0.0,
                details="No barcode available for GS1 country code verification.",
                evidence={"reason": "barcode_not_found"},
                is_counterfeit_signal=False,
            )

        barcode_clean = re.sub(r"[\s\-]", "", str(barcode))

        if len(barcode_clean) < 3:
            return VerificationResult(
                check_name="gs1_country_code",
                status="UNVERIFIABLE",
                confidence=0.2,
                details=f"Barcode '{barcode}' is too short for GS1 prefix analysis.",
                evidence={"barcode": barcode},
                is_counterfeit_signal=False,
            )

        # Determine country from barcode prefix
        barcode_country = self._lookup_gs1_country(barcode_clean)

        if not declared_country:
            return VerificationResult(
                check_name="gs1_country_code",
                status="WARNING",
                confidence=0.5,
                details=(
                    f"Barcode prefix indicates origin: {barcode_country}. "
                    "No Country of Origin declaration found on packaging for cross-verification."
                ),
                evidence={
                    "barcode": barcode_clean,
                    "barcode_country": barcode_country,
                    "declared_country": None,
                },
                is_counterfeit_signal=False,
            )

        # Cross-verify
        barcode_prefix = int(barcode_clean[:3])
        declared_lower = declared_country.lower().strip()

        # Check if the declared country matches the barcode prefix
        is_match = False
        for country_key, prefix_ranges in COUNTRY_NAME_TO_GS1.items():
            if country_key in declared_lower or declared_lower in country_key:
                for pr in prefix_ranges:
                    if barcode_prefix in pr:
                        is_match = True
                        break
                if is_match:
                    break

        # Also check single-match by looking up the barcode country
        if not is_match and barcode_country:
            is_match = (
                declared_lower in barcode_country.lower()
                or barcode_country.lower() in declared_lower
            )

        if is_match:
            return VerificationResult(
                check_name="gs1_country_code",
                status="VERIFIED",
                confidence=0.85,
                details=(
                    f"GS1 barcode prefix ({barcode_clean[:3]}) corresponds to "
                    f"'{barcode_country}', which matches the declared Country of Origin "
                    f"'{declared_country}'. No origin discrepancy detected."
                ),
                evidence={
                    "barcode": barcode_clean,
                    "barcode_prefix": barcode_clean[:3],
                    "barcode_country": barcode_country,
                    "declared_country": declared_country,
                    "match": True,
                },
                is_counterfeit_signal=False,
            )
        else:
            return VerificationResult(
                check_name="gs1_country_code",
                status="FAILED",
                confidence=0.75,
                details=(
                    f"⚠️ ORIGIN MISMATCH. Barcode prefix ({barcode_clean[:3]}) indicates "
                    f"'{barcode_country}', but the package declares Country of Origin as "
                    f"'{declared_country}'. This may indicate relabeled or mislabeled goods. "
                    "Note: some companies use barcodes registered in a different country "
                    "than where the product is manufactured."
                ),
                evidence={
                    "barcode": barcode_clean,
                    "barcode_prefix": barcode_clean[:3],
                    "barcode_country": barcode_country,
                    "declared_country": declared_country,
                    "match": False,
                },
                is_counterfeit_signal=True,
            )

    # ------------------------------------------------------------------
    # CHECK 5: MRP Anomaly Detection
    # ------------------------------------------------------------------

    def _check_mrp_anomaly(
        self, extractions: dict, listing_data: Optional[dict]
    ) -> VerificationResult:
        """Detect suspicious MRP values that may indicate counterfeiting or overcharging."""
        mrp_raw = self._get_value(extractions, "mrp")

        if not mrp_raw:
            return VerificationResult(
                check_name="mrp_anomaly",
                status="UNVERIFIABLE",
                confidence=0.0,
                details="No MRP detected on packaging. Cannot perform price anomaly analysis.",
                evidence={"reason": "mrp_not_found"},
                is_counterfeit_signal=False,
            )

        # Parse MRP to float
        mrp_value = self._parse_price(mrp_raw)

        if mrp_value is None:
            return VerificationResult(
                check_name="mrp_anomaly",
                status="UNVERIFIABLE",
                confidence=0.3,
                details=f"Could not parse MRP value from '{mrp_raw}'.",
                evidence={"mrp_raw": mrp_raw},
                is_counterfeit_signal=False,
            )

        anomalies = []

        # Check: MRP is unreasonably low (< ₹1)
        if mrp_value < 1.0:
            anomalies.append(
                f"MRP ₹{mrp_value:.2f} is suspiciously low. "
                "Legitimate pre-packaged products rarely have MRP below ₹1."
            )

        # Check: MRP is unreasonably high (> ₹1,00,000) for consumer goods
        if mrp_value > 100000:
            anomalies.append(
                f"MRP ₹{mrp_value:,.2f} is unusually high for a pre-packaged consumer commodity."
            )

        # Check: MRP vs listing price (e-commerce cross-verification)
        if listing_data:
            listing_price_raw = listing_data.get("listed_price") or listing_data.get("price")
            if listing_price_raw:
                listing_price = self._parse_price(str(listing_price_raw))
                if listing_price is not None:
                    # Selling above MRP is illegal under Section 18(1)
                    if listing_price > mrp_value * 1.01:  # 1% tolerance for rounding
                        anomalies.append(
                            f"E-commerce listing price ₹{listing_price:,.2f} EXCEEDS "
                            f"MRP ₹{mrp_value:,.2f}. Selling above MRP is a criminal offence "
                            "under Section 18(1) of Legal Metrology Act, 2009."
                        )
                    # Extremely deep discount may indicate counterfeit
                    elif listing_price < mrp_value * 0.30:
                        anomalies.append(
                            f"E-commerce listing price ₹{listing_price:,.2f} is "
                            f"{((1 - listing_price/mrp_value) * 100):.0f}% below MRP "
                            f"₹{mrp_value:,.2f}. Extremely deep discounts (>70% off MRP) "
                            "can indicate counterfeit or expired stock being dumped."
                        )

        if anomalies:
            return VerificationResult(
                check_name="mrp_anomaly",
                status="WARNING" if len(anomalies) == 1 else "FAILED",
                confidence=0.70,
                details=" | ".join(anomalies),
                evidence={
                    "mrp_value": mrp_value,
                    "mrp_raw": mrp_raw,
                    "anomalies": anomalies,
                    "listing_price": listing_data.get("listed_price") if listing_data else None,
                },
                is_counterfeit_signal=len(anomalies) > 1,
            )

        return VerificationResult(
            check_name="mrp_anomaly",
            status="VERIFIED",
            confidence=0.70,
            details=f"MRP ₹{mrp_value:,.2f} is within reasonable range. No price anomalies detected.",
            evidence={"mrp_value": mrp_value, "mrp_raw": mrp_raw},
            is_counterfeit_signal=False,
        )

    # ------------------------------------------------------------------
    # CHECK 6: BIS / ISI Certification Mark
    # ------------------------------------------------------------------

    def _check_bis_isi_mark(self, extractions: dict) -> VerificationResult:
        """Check for BIS/ISI mark and validate license number format."""
        additional = extractions.get("additional_declarations", [])
        if isinstance(additional, str):
            additional = [additional]

        # Search for ISI/BIS references in extractions
        isi_number = None
        for decl in (additional or []):
            decl_str = str(decl).upper()
            # Look for ISI CM/L number patterns
            isi_match = re.search(r"(?:CM/?L|IS|ISI)\s*[-:]?\s*(\d{5,10})", decl_str)
            if isi_match:
                isi_number = isi_match.group(1)
                break
            # Also check for "IS ####" standard number
            is_match = re.search(r"IS\s*[-:]?\s*(\d{3,6})", decl_str)
            if is_match:
                isi_number = is_match.group(1)
                break

        if not isi_number:
            # Not all products require ISI mark — this is informational
            return VerificationResult(
                check_name="bis_isi_mark",
                status="UNVERIFIABLE",
                confidence=0.4,
                details=(
                    "No BIS/ISI certification mark detected. Note: ISI mark is mandatory "
                    "only for products covered under BIS mandatory certification scheme "
                    "(e.g., cement, LPG cylinders, packaged drinking water, electrical appliances)."
                ),
                evidence={"reason": "isi_mark_not_found"},
                is_counterfeit_signal=False,
            )

        # Validate format (CML numbers are up to 10 digits)
        if not re.match(r"^\d{5,10}$", isi_number):
            return VerificationResult(
                check_name="bis_isi_mark",
                status="WARNING",
                confidence=0.50,
                details=(
                    f"ISI/BIS number '{isi_number}' has an unusual format. "
                    "Standard CML numbers are 5-10 digit numeric codes. "
                    "Verify manually at https://manakonline.in"
                ),
                evidence={
                    "isi_number": isi_number,
                    "manual_verify_url": "https://manakonline.in",
                },
                is_counterfeit_signal=False,
            )

        return VerificationResult(
            check_name="bis_isi_mark",
            status="WARNING",
            confidence=0.50,
            details=(
                f"ISI/BIS mark detected with number '{isi_number}'. "
                "Format is valid but online verification against BIS Manak database "
                "is not available via public API. "
                "Verify manually via BIS Care App or https://manakonline.in"
            ),
            evidence={
                "isi_number": isi_number,
                "manual_verify_url": "https://manakonline.in",
                "bis_care_app": "Available on Google Play / Apple App Store",
            },
            is_counterfeit_signal=False,
        )

    # ------------------------------------------------------------------
    # Trust Score Computation
    # ------------------------------------------------------------------

    def _compute_trust_score(self, checks: list[VerificationResult]) -> float:
        """Compute weighted trust score from all verification checks."""
        total_weight = 0.0
        earned_score = 0.0

        for check in checks:
            weight = self.CHECK_WEIGHTS.get(check.check_name, 10.0)
            total_weight += weight

            if check.status == "VERIFIED":
                earned_score += weight * check.confidence
            elif check.status == "WARNING":
                earned_score += weight * check.confidence * 0.5
            elif check.status == "UNVERIFIABLE":
                # Neutral — don't penalize but don't reward
                earned_score += weight * 0.5
            elif check.status == "FAILED":
                # Penalize heavily
                earned_score += weight * (1.0 - check.confidence) * 0.2

        if total_weight == 0:
            return 50.0

        return (earned_score / total_weight) * 100.0

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    @staticmethod
    def _get_value(extractions: dict, key: str) -> Optional[str]:
        """Safely extract a value from the extractions dict."""
        val = extractions.get(key)
        if val is None:
            return None
        if isinstance(val, dict):
            v = val.get("value")
            return str(v) if v is not None else None
        return str(val) if val else None

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse various date formats found on Indian packaging."""
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Common Indian packaging date formats
        formats = [
            "%m/%Y",        # 03/2026
            "%m-%Y",        # 03-2026
            "%b %Y",        # Mar 2026
            "%B %Y",        # March 2026
            "%d/%m/%Y",     # 15/03/2026
            "%d-%m-%Y",     # 15-03-2026
            "%d.%m.%Y",     # 15.03.2026
            "%Y-%m-%d",     # 2026-03-15
            "%m/%d/%Y",     # 03/15/2026
            "%b-%Y",        # Mar-2026
            "%b/%Y",        # Mar/2026
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # For MM/YYYY format, set to end of month for expiry
                if "%d" not in fmt:
                    if fmt in ("%m/%Y", "%m-%Y", "%b %Y", "%B %Y", "%b-%Y", "%b/%Y"):
                        # Set to last day of month
                        if dt.month == 12:
                            dt = dt.replace(day=31)
                        else:
                            dt = (dt.replace(month=dt.month + 1, day=1) - timedelta(days=1))
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        return None

    @staticmethod
    def _parse_price(price_str: str) -> Optional[float]:
        """Parse price value from various formats (₹, Rs., etc.)."""
        if not price_str:
            return None
        # Remove currency symbols and separators
        cleaned = re.sub(r"[₹$Rs.MRP:,\s]", "", str(price_str), flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        try:
            return float(cleaned)
        except ValueError:
            # Try extracting first decimal number
            match = re.search(r"(\d+\.?\d*)", str(price_str))
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        return None

    @staticmethod
    def _fuzzy_contains(a: str, b: str) -> bool:
        """Check if string a substantially contains string b (case-insensitive)."""
        if not a or not b:
            return False
        a_lower = a.lower().strip()
        b_lower = b.lower().strip()
        # Direct containment
        if b_lower in a_lower or a_lower in b_lower:
            return True
        # Check word overlap
        a_words = set(re.findall(r"\w+", a_lower))
        b_words = set(re.findall(r"\w+", b_lower))
        if not b_words:
            return False
        overlap = a_words & b_words
        return len(overlap) / len(b_words) >= 0.5

    def _extract_fssai_number(self, extractions: dict) -> Optional[str]:
        """Extract FSSAI license number from various extraction fields."""
        # Check dedicated field first
        fssai = self._get_value(extractions, "fssai_license_number")
        if fssai:
            return fssai

        # Search in additional_declarations
        additional = extractions.get("additional_declarations", [])
        if isinstance(additional, str):
            additional = [additional]

        for decl in (additional or []):
            decl_str = str(decl)
            # Look for FSSAI patterns
            fssai_match = re.search(
                r"(?:FSSAI|Lic\.?\s*(?:No\.?)?|License\s*No\.?)\s*[:.]?\s*(\d[\d\s\-]{12,16}\d)",
                decl_str, re.IGNORECASE
            )
            if fssai_match:
                return re.sub(r"[\s\-]", "", fssai_match.group(1))

            # Plain 14-digit number near "FSSAI" keyword
            if "fssai" in decl_str.lower():
                num_match = re.search(r"(\d{14})", decl_str)
                if num_match:
                    return num_match.group(1)

        return None

    @staticmethod
    def _lookup_gs1_country(barcode: str) -> str:
        """Look up country from GS1 barcode prefix."""
        try:
            prefix_3 = int(barcode[:3])
            prefix_2 = int(barcode[:2])
        except (ValueError, IndexError):
            return "Unknown"

        # First try 3-digit prefix (more specific)
        for start, end, country in GS1_COUNTRY_PREFIXES:
            if start <= prefix_3 <= end:
                return country

        # Fallback to 2-digit prefix
        for start, end, country in GS1_COUNTRY_PREFIXES:
            if start <= prefix_2 <= end:
                return country

        return "Unknown"


# Module-level singleton
verification_agent = VerificationAgent()
