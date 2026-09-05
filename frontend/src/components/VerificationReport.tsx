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
    bg: "rgba(0, 255, 100, 0.1)",
    color: "#00ff64",
    icon: <CheckCircle2 size={16} />,
  },
  FAILED: {
    bg: "rgba(255, 50, 50, 0.1)",
    color: "#ff4444",
    icon: <XCircle size={16} />,
  },
  WARNING: {
    bg: "rgba(255, 171, 0, 0.1)",
    color: "#ffab00",
    icon: <AlertTriangle size={16} />,
  },
  UNVERIFIABLE: {
    bg: "rgba(120, 130, 170, 0.1)",
    color: "rgba(160, 170, 210, 0.7)",
    icon: <HelpCircle size={16} />,
  },
};

export default function VerificationReport({ verification }: VerificationReportProps) {
  const { trust_score, overall_status, checks, counterfeit_signals, expiry_status, days_until_expiry } = verification;

  // Verdict styling
  const verdictConfig: Record<string, { color: string; gradient: string; icon: React.ReactNode; label: string }> = {
    AUTHENTIC: {
      color: "#00ff64",
      gradient: "linear-gradient(135deg, rgba(0, 255, 100, 0.08), rgba(0, 200, 80, 0.04))",
      icon: <ShieldCheck size={32} />,
      label: "AUTHENTIC",
    },
    SUSPICIOUS: {
      color: "#ffab00",
      gradient: "linear-gradient(135deg, rgba(255, 171, 0, 0.08), rgba(255, 140, 0, 0.04))",
      icon: <ShieldAlert size={32} />,
      label: "SUSPICIOUS",
    },
    COUNTERFEIT_RISK: {
      color: "#ff4444",
      gradient: "linear-gradient(135deg, rgba(255, 50, 50, 0.08), rgba(255, 30, 30, 0.04))",
      icon: <ShieldX size={32} />,
      label: "COUNTERFEIT RISK",
    },
  };

  const verdict = verdictConfig[overall_status] || verdictConfig.SUSPICIOUS;

  // Expiry status styling
  const expiryConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    VALID: { color: "#00ff64", icon: <CheckCircle2 size={16} />, label: "Valid" },
    EXPIRED: { color: "#ff4444", icon: <Skull size={16} />, label: "EXPIRED" },
    NEAR_EXPIRY: { color: "#ffab00", icon: <Timer size={16} />, label: "Near Expiry" },
    DATE_TAMPERED: { color: "#ff4444", icon: <AlertTriangle size={16} />, label: "Date Tampered!" },
    UNKNOWN: { color: "rgba(160, 170, 210, 0.7)", icon: <HelpCircle size={16} />, label: "Unknown" },
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
                stroke="rgba(255,255,255,0.06)"
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
                color: "rgba(180, 190, 220, 0.6)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
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
            borderRadius: "14px",
            background: `${expiry.color}0a`,
            border: `1px solid ${expiry.color}20`,
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
                  color: "rgba(180, 190, 220, 0.7)",
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
            borderRadius: "14px",
            background: counterfeit_signals > 0
              ? "rgba(255, 50, 50, 0.06)"
              : "rgba(0, 255, 100, 0.06)",
            border: `1px solid ${counterfeit_signals > 0 ? "rgba(255, 50, 50, 0.15)" : "rgba(0, 255, 100, 0.15)"}`,
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
          }}>
            {counterfeit_signals > 0
              ? <AlertTriangle size={18} color="#ff4444" />
              : <CheckCircle2 size={18} color="#00ff64" />}
            <div>
              <div style={{
                color: counterfeit_signals > 0 ? "#ff4444" : "#00ff64",
                fontSize: "0.8rem",
                fontWeight: 700,
              }}>
                {counterfeit_signals > 0
                  ? `${counterfeit_signals} Fraud Signal${counterfeit_signals > 1 ? "s" : ""} Detected`
                  : "No Fraud Signals"}
              </div>
              <div style={{ color: "rgba(180, 190, 220, 0.6)", fontSize: "0.7rem", marginTop: "2px" }}>
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
              { label: "Passed", count: checks.filter((c) => c.status === "VERIFIED").length, color: "#00ff64" },
              { label: "Failed", count: checks.filter((c) => c.status === "FAILED").length, color: "#ff4444" },
              { label: "Warning", count: checks.filter((c) => c.status === "WARNING").length, color: "#ffab00" },
            ].map((s) => (
              <div key={s.label} style={{
                textAlign: "center",
                padding: "0.5rem",
                borderRadius: "10px",
                background: `${s.color}08`,
                border: `1px solid ${s.color}15`,
              }}>
                <div style={{ fontSize: "1.2rem", fontWeight: 800, color: s.color }}>{s.count}</div>
                <div style={{ fontSize: "0.65rem", color: "rgba(180, 190, 220, 0.6)" }}>{s.label}</div>
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
          color: "rgba(180, 190, 220, 0.8)",
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
        borderRadius: "14px",
        background: "rgba(15, 20, 40, 0.6)",
        border: `1px solid ${statusStyle.color}20`,
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
            fontWeight: 600,
            color: "rgba(220, 225, 245, 0.9)",
          }}>
            {meta.label}
          </span>
        </div>

        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "0.4rem",
          padding: "0.25rem 0.75rem",
          borderRadius: "8px",
          background: statusStyle.bg,
          border: `1px solid ${statusStyle.color}25`,
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
        fontSize: "0.8rem",
        color: "rgba(180, 190, 220, 0.75)",
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
        <span style={{ fontSize: "0.65rem", color: "rgba(150, 160, 200, 0.5)" }}>
          Confidence
        </span>
        <div style={{
          flex: 1,
          height: "4px",
          borderRadius: "2px",
          background: "rgba(255, 255, 255, 0.05)",
          overflow: "hidden",
        }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${check.confidence * 100}%` }}
            transition={{ delay: index * 0.08 + 0.3, duration: 0.6 }}
            style={{
              height: "100%",
              borderRadius: "2px",
              background: statusStyle.color,
              opacity: 0.7,
            }}
          />
        </div>
        <span style={{
          fontSize: "0.65rem",
          color: "rgba(150, 160, 200, 0.5)",
          fontFamily: "monospace",
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
          borderRadius: "8px",
          background: "rgba(255, 50, 50, 0.08)",
          border: "1px solid rgba(255, 50, 50, 0.15)",
          alignSelf: "flex-start",
        }}>
          <AlertTriangle size={13} color="#ff4444" />
          <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#ff4444" }}>
            COUNTERFEIT SIGNAL
          </span>
        </div>
      )}
    </motion.div>
  );
}
