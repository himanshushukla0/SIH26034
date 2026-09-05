"""
SIH26034 LMPC Compliance Engine — Database Models

SQLAlchemy ORM models for persisting audit results, violations,
verification checks, and product metadata. Supports audit history,
analytics queries, authenticity verification, and violation trend tracking.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AuditInputType(str, enum.Enum):
    """How the audit was initiated."""
    IMAGE = "image"
    URL = "url"
    CAMERA = "camera"


class AuditStatus(str, enum.Enum):
    """Current processing state of the audit."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ViolationSeverity(str, enum.Enum):
    """Severity classification per LMPC violation taxonomy."""
    CRITICAL = "critical"   # Missing MRP, Altered MRP, Missing Expiry on perishables
    MAJOR = "major"         # Missing USP, Incomplete Consumer Care, Non-standard units
    MINOR = "minor"         # Font height slightly below threshold, poor contrast


class VerificationStatus(str, enum.Enum):
    """Result status for each authenticity verification check."""
    VERIFIED = "verified"           # Confirmed authentic against external source
    FAILED = "failed"               # External source contradicts package claims
    WARNING = "warning"             # Suspicious but not definitively fraudulent
    UNVERIFIABLE = "unverifiable"   # External source unavailable or data insufficient


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Audit(Base):
    """
    Represents a single compliance audit — either from a packaging image
    or an e-commerce URL. Tracks the overall score and links to individual
    violation records.
    """
    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    input_type: Mapped[AuditInputType] = mapped_column(Enum(AuditInputType))
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus), default=AuditStatus.PENDING
    )

    # --- Compliance Results ---
    compliance_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0.0 — 100.0
    overall_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # "COMPLIANT", "NON_COMPLIANT", "PARTIAL_VIOLATION", "NEEDS_MANUAL_REVIEW"
    total_checks: Mapped[int] = mapped_column(Integer, default=10)
    passed_checks: Mapped[int] = mapped_column(Integer, default=0)
    failed_checks: Mapped[int] = mapped_column(Integer, default=0)

    # --- Product Info (extracted) ---
    product_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mrp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    net_quantity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # --- Report ---
    report_pdf_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_extractions_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Full JSON blob from Vision Agent

    # --- Authenticity Verification ---
    trust_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0.0 — 100.0 authenticity trust score
    expiry_status: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # "VALID", "EXPIRED", "NEAR_EXPIRY", "DATE_TAMPERED"
    is_expired: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, default=False
    )
    days_until_expiry: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Negative = already expired X days ago
    barcode_number: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # Decoded EAN-13 / GTIN from scanner
    fssai_license_number: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # 14-digit FSSAI license extracted from package

    # --- Relationships ---
    violations: Mapped[list["Violation"]] = relationship(
        back_populates="audit", cascade="all, delete-orphan"
    )
    verification_checks: Mapped[list["VerificationCheck"]] = relationship(
        back_populates="audit", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Audit id={self.id[:8]}... score={self.compliance_score} "
            f"status={self.status.value}>"
        )


class Violation(Base):
    """
    Represents a single regulatory violation detected during an audit.
    References the specific LMPC Rule and Act Section with prescribed statutory penalties.
    """
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audits.id", ondelete="CASCADE")
    )

    # --- Statutory Violation Details ---
    rule_reference: Mapped[str] = mapped_column(
        String(150)
    )  # e.g. "Rule 6(1)(f) - LM(PC) Rules, 2011"
    act_section: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True
    )  # e.g. "Section 18(1) - Legal Metrology Act, 2009"
    punishment_section: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True
    )  # e.g. "Section 36(1) - Legal Metrology Act, 2009"
    statutory_penalty: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Prescribed statutory fine / imprisonment clause
    legal_proof_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Formal statutory justification
    field_name: Mapped[str] = mapped_column(
        String(100)
    )  # e.g. "MRP", "Unit Sale Price", "Country of Origin"
    severity: Mapped[ViolationSeverity] = mapped_column(Enum(ViolationSeverity))
    description: Mapped[str] = mapped_column(
        Text
    )  # Human-readable explanation of what's wrong
    expected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    found_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Cross-modal (e-commerce) ---
    is_discrepancy: Mapped[bool] = mapped_column(
        default=False
    )  # True if web listing vs. physical packaging mismatch

    # --- Relationships ---
    audit: Mapped["Audit"] = relationship(back_populates="violations")

    def __repr__(self) -> str:
        return (
            f"<Violation rule={self.rule_reference} field={self.field_name} "
            f"severity={self.severity.value}>"
        )


class VerificationCheck(Base):
    """
    Represents a single authenticity verification check performed during an audit.
    Each audit can have up to 6 checks (barcode, FSSAI, expiry, GS1, MRP, BIS).
    """
    __tablename__ = "verification_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audits.id", ondelete="CASCADE")
    )

    # --- Check Identity ---
    check_name: Mapped[str] = mapped_column(
        String(50)
    )  # "barcode_identity", "fssai_license", "expiry_validation",
       # "gs1_country_code", "mrp_anomaly", "bis_isi_mark"

    # --- Result ---
    status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 — 1.0
    details: Mapped[str] = mapped_column(Text)  # Human-readable result explanation
    evidence_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Raw JSON response from external verification source
    is_counterfeit_signal: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # True = this check suggests counterfeiting

    # --- Relationships ---
    audit: Mapped["Audit"] = relationship(back_populates="verification_checks")

    def __repr__(self) -> str:
        return (
            f"<VerificationCheck check={self.check_name} "
            f"status={self.status.value} counterfeit={self.is_counterfeit_signal}>"
        )
