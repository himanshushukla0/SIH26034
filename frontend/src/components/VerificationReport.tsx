/**
 * SIH26034 — Verification Report Component
 *
 * Displays the 6-check authenticity verification breakdown
 * with a Trust Score gauge, per-check cards, and expiry status.
 */

import { motion } from "framer-motion";
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Barcode,
  FileCheck2,
  Clock,
  Globe,
  IndianRupee,
  Award,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Timer,
  Skull,
} from "lucide-react";
import type { PackageAuthenticityVerdict, VerificationCheck } from "../api";

interface VerificationReportProps {
  verification: PackageAuthenticityVerdict;
}

/** Human-readable check names. */
const CHECK_LABELS: Record<string, { label: string; icon: React.ReactNode }> = {
  barcode_identity: { label: "Barcode Identity", icon: <Barcode size={18} /> },
  fssai_license: { label: "FSSAI License", icon: <FileCheck2 size={18} /> },
  expiry_validation: { label: "Expiry & Shelf Life", icon: <Clock size={18} /> },
  gs1_country_code: { label: "Country of Origin", icon: <Globe size={18} /> },
  mrp_anomaly: { label: "MRP Integrity", icon: <IndianRupee size={18} /> },
  bis_isi_mark: { label: "BIS / ISI Mark", icon: <Award size={18} /> },
};

/** Status badge colors. */
const STATUS_STYLES: Record<string, { bg: string; color: string; icon: React.ReactNode }> = {
  VERIFIED: {
    bg: "#ecfdf5",
    color: "#15803d",
    icon: <CheckCircle2 size={16} />,
  },
  FAILED: {
    bg: "#fef2f2",
    color: "#b91c1c",
    icon: <XCircle size={16} />,
  },
  WARNING: {
    bg: "#fffbeb",
    color: "#b45309",
    icon: <AlertTriangle size={16} />,
  },
  UNVERIFIABLE: {
    bg: "#f1f5f9",
    color: "#64748b",
    icon: <HelpCircle size={16} />,
  },
};

export default function VerificationReport({ verification }: VerificationReportProps) {
  const { trust_score, overall_status, checks, counterfeit_signals, expiry_status, days_until_expiry } = verification;

  // Verdict styling
  const verdictConfig: Record<string, { color: string; gradient: string; icon: React.ReactNode; label: string }> = {
    AUTHENTIC: {
      color: "#15803d",
      gradient: "linear-gradient(135deg, #f0fdf4, #dcfce7)",
      icon: <ShieldCheck size={32} />,
      label: "AUTHENTIC",
    },
    SUSPICIOUS: {
      color: "#b45309",
      gradient: "linear-gradient(135deg, #fffbeb, #fef3c7)",
      icon: <ShieldAlert size={32} />,
      label: "SUSPICIOUS",
    },
    COUNTERFEIT_RISK: {
      color: "#b91c1c",
      gradient: "linear-gradient(135deg, #fef2f2, #fee2e2)",
      icon: <ShieldX size={32} />,
      label: "COUNTERFEIT RISK",
    },
  };

  const verdict = verdictConfig[overall_status] || verdictConfig.SUSPICIOUS;

  // Expiry status styling
  const expiryConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    VALID: { color: "#15803d", icon: <CheckCircle2 size={16} />, label: "Valid" },
    EXPIRED: { color: "#b91c1c", icon: <Skull size={16} />, label: "EXPIRED" },
    NEAR_EXPIRY: { color: "#b45309", icon: <Timer size={16} />, label: "Near Expiry" },
    DATE_TAMPERED: { color: "#b91c1c", icon: <AlertTriangle size={16} />, label: "Date Tampered!" },
    UNKNOWN: { color: "#64748b", icon: <HelpCircle size={16} />, label: "Unknown" },
  };

  const expiry = expiryConfig[expiry_status] || expiryConfig.UNKNOWN;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "1.25rem",
        width: "100%",
      }}
    >
      {/* ── Header: Trust Score & Verdict ── */}
      <div style={{
        display: "flex",
        gap: "1.25rem",
        flexWrap: "wrap",
      }}>
        {/* Trust Score */}
        <motion.div
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          style={{
            flex: "1 1 200px",
            padding: "1.5rem",
            borderRadius: "20px",
            background: verdict.gradient,
            border: `1px solid ${verdict.color}25`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.75rem",
          }}
        >
          <div style={{ color: verdict.color }}>{verdict.icon}</div>

          {/* Circular Trust Score */}
          <div style={{ position: "relative", width: "100px", height: "100px" }}>
            <svg viewBox="0 0 100 100" style={{ transform: "rotate(-90deg)" }}>
              {/* Background circle */}
              <circle
                cx="50" cy="50" r="42"
                fill="none"
                stroke="#e2e8f0"
                strokeWidth="8"
              />
              {/* Score arc */}
              <motion.circle
                cx="50" cy="50" r="42"
                fill="none"
                stroke={verdict.color}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${(trust_score / 100) * 264} 264`}
                initial={{ strokeDasharray: "0 264" }}
                animate={{ strokeDasharray: `${(trust_score / 100) * 264} 264` }}
                transition={{ duration: 1.2, ease: "easeOut" }}
              />
            </svg>
            <div style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}>
              <span style={{
                fontSize: "1.5rem",
                fontWeight: 800,
                color: verdict.color,
                lineHeight: 1,
              }}>
                {Math.round(trust_score)}
              </span>
              <span style={{
                fontSize: "0.6rem",
                color: "#64748b",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                fontWeight: 700,
              }}>
                Trust
              </span>
            </div>
          </div>

          <div style={{
            fontSize: "0.85rem",
            fontWeight: 700,
            color: verdict.color,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}>
            {verdict.label}
          </div>
        </motion.div>

        {/* Summary Stats */}
        <div style={{
          flex: "1 1 200px",
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
        }}>
          {/* Expiry Status */}
          <div style={{
            padding: "1rem 1.25rem",
            borderRadius: "10px",
            background: "#ffffff",
            border: `1px solid var(--border)`,
            boxShadow: "var(--shadow-card)",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
          }}>
            <div style={{ color: expiry.color }}>{expiry.icon}</div>
            <div>
              <div style={{ color: expiry.color, fontSize: "0.8rem", fontWeight: 700 }}>
                {expiry.label}
              </div>
              {days_until_expiry !== null && days_until_expiry !== undefined && (
                <div style={{
                  color: "#64748b",
                  fontSize: "0.75rem",
                  marginTop: "2px",
                }}>
                  {days_until_expiry < 0
                    ? `Expired ${Math.abs(days_until_expiry)} days ago`
                    : `${days_until_expiry} days remaining`}
                </div>
              )}
            </div>
          </div>

          {/* Counterfeit Signals */}
          <div style={{
            padding: "1rem 1.25rem",
            borderRadius: "10px",
            background: "#ffffff",
            border: `1px solid var(--border)`,
            boxShadow: "var(--shadow-card)",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
          }}>
            {counterfeit_signals > 0
              ? <AlertTriangle size={18} color="#b91c1c" />
              : <CheckCircle2 size={18} color="#15803d" />}
            <div>
              <div style={{
                color: counterfeit_signals > 0 ? "#b91c1c" : "#15803d",
                fontSize: "0.8rem",
                fontWeight: 700,
              }}>
                {counterfeit_signals > 0
                  ? `${counterfeit_signals} Fraud Signal${counterfeit_signals > 1 ? "s" : ""} Detected`
                  : "No Fraud Signals"}
              </div>
              <div style={{ color: "#64748b", fontSize: "0.7rem", marginTop: "2px" }}>
                {checks.filter((c) => c.status === "VERIFIED").length} / {checks.length} checks passed
              </div>
            </div>
          </div>

          {/* Checks Passed / Failed / Warning */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "0.5rem",
          }}>
            {[
              { label: "Passed", count: checks.filter((c) => c.status === "VERIFIED").length, color: "#15803d", bg: "#f0fdf4" },
              { label: "Failed", count: checks.filter((c) => c.status === "FAILED").length, color: "#b91c1c", bg: "#fef2f2" },
              { label: "Warning", count: checks.filter((c) => c.status === "WARNING").length, color: "#b45309", bg: "#fffbeb" },
            ].map((s) => (
              <div key={s.label} style={{
                textAlign: "center",
                padding: "0.5rem",
                borderRadius: "8px",
                background: s.bg,
                border: `1px solid var(--border)`,
              }}>
                <div style={{ fontSize: "1.2rem", fontWeight: 800, color: s.color }}>{s.count}</div>
                <div style={{ fontSize: "0.65rem", color: "#64748b", fontWeight: 600 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Per-Check Cards ── */}
      <div style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
      }}>
        <h3 style={{
          fontSize: "0.85rem",
          fontWeight: 700,
          color: "var(--gov-navy-dark)",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          margin: 0,
        }}>
          Verification Checks
        </h3>

        {checks.map((check, idx) => (
          <CheckCard key={check.check_name} check={check} index={idx} />
        ))}
      </div>
    </motion.div>
  );
}


function CheckCard({ check, index }: { check: VerificationCheck; index: number }) {
  const meta = CHECK_LABELS[check.check_name] || { label: check.check_name, icon: <HelpCircle size={18} /> };
  const statusStyle = STATUS_STYLES[check.status] || STATUS_STYLES.UNVERIFIABLE;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08, duration: 0.3 }}
      style={{
        padding: "1rem 1.25rem",
        borderRadius: "10px",
        background: "#ffffff",
        border: "1px solid var(--border)",
        boxShadow: "var(--shadow-card)",
        display: "flex",
        flexDirection: "column",
        gap: "0.6rem",
      }}
    >
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <div style={{ color: statusStyle.color }}>{meta.icon}</div>
          <span style={{
            fontSize: "0.9rem",
            fontWeight: 700,
            color: "var(--gov-navy-dark)",
          }}>
            {meta.label}
          </span>
        </div>

        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "0.4rem",
          padding: "0.25rem 0.75rem",
          borderRadius: "6px",
          background: statusStyle.bg,
          border: `1px solid ${statusStyle.color}40`,
        }}>
          <span style={{ color: statusStyle.color }}>{statusStyle.icon}</span>
          <span style={{
            fontSize: "0.7rem",
            fontWeight: 700,
            color: statusStyle.color,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
          }}>
            {check.status}
          </span>
        </div>
      </div>

      {/* Details */}
      <p style={{
        margin: 0,
        fontSize: "0.85rem",
        color: "#334155",
        lineHeight: 1.5,
      }}>
        {check.details}
      </p>

      {/* Confidence Bar */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
      }}>
        <span style={{ fontSize: "0.68rem", color: "#64748b", fontWeight: 600 }}>
          Confidence
        </span>
        <div style={{
          flex: 1,
          height: "6px",
          borderRadius: "3px",
          background: "#e2e8f0",
          overflow: "hidden",
        }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${check.confidence * 100}%` }}
            transition={{ delay: index * 0.08 + 0.3, duration: 0.6 }}
            style={{
              height: "100%",
              borderRadius: "3px",
              background: statusStyle.color,
            }}
          />
        </div>
        <span style={{
          fontSize: "0.7rem",
          color: "#475569",
          fontFamily: "var(--font-mono)",
          fontWeight: 600,
          minWidth: "2.5rem",
          textAlign: "right",
        }}>
          {(check.confidence * 100).toFixed(0)}%
        </span>
      </div>

      {/* Counterfeit Signal Badge */}
      {check.is_counterfeit_signal && (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "0.4rem",
          padding: "0.4rem 0.75rem",
          borderRadius: "6px",
          background: "#fef2f2",
          border: "1px solid #fecaca",
          alignSelf: "flex-start",
        }}>
          <AlertTriangle size={13} color="#b91c1c" />
          <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#b91c1c" }}>
            COUNTERFEIT SIGNAL
          </span>
        </div>
      )}
    </motion.div>
  );
}
