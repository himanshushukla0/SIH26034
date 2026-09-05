import { motion } from "framer-motion";
import { AlertTriangle, AlertCircle, Info } from "lucide-react";
import type { Violation } from "../api";

interface ViolationCardProps {
  violation: Violation;
  index: number;
}

function getSeverityIcon(severity: string) {
  switch (severity) {
    case "critical":
      return <AlertTriangle size={16} />;
    case "major":
      return <AlertCircle size={16} />;
    default:
      return <Info size={16} />;
  }
}

export default function ViolationCard({ violation, index }: ViolationCardProps) {
  return (
    <motion.div
      className={`glass-card violation-card severity-${violation.severity}`}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
    >
      <div className="violation-header" style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
        <span className="violation-rule">{violation.rule_reference}</span>
        {violation.act_section && (
          <span style={{ fontSize: "0.75rem", background: "rgba(14, 165, 233, 0.15)", color: "#38bdf8", padding: "2px 8px", borderRadius: "4px", fontWeight: 600 }}>
            🏛️ {violation.act_section}
          </span>
        )}
        {violation.punishment_section && (
          <span style={{ fontSize: "0.75rem", background: "rgba(239, 68, 68, 0.15)", color: "#f87171", padding: "2px 8px", borderRadius: "4px", fontWeight: 600 }}>
            ⚖️ {violation.punishment_section}
          </span>
        )}
        <span className={`badge badge-${violation.severity}`} style={{ marginLeft: "auto" }}>
          {getSeverityIcon(violation.severity)}
          {violation.severity}
        </span>
      </div>

      <div className="violation-field">{violation.field_name}</div>
      <div className="violation-desc">{violation.description}</div>

      {violation.legal_proof_summary && (
        <div style={{ marginTop: "8px", padding: "8px 12px", background: "rgba(255, 255, 255, 0.03)", borderLeft: "3px solid #38bdf8", borderRadius: "4px", fontSize: "0.8rem", color: "#cbd5e1", lineHeight: 1.5 }}>
          <strong style={{ color: "#38bdf8" }}>Statutory Proof:</strong> {violation.legal_proof_summary}
        </div>
      )}

      {(violation.expected_value || violation.found_value) && (
        <div className="violation-values">
          {violation.expected_value && (
            <span className="violation-expected">
              Expected: {violation.expected_value}
            </span>
          )}
          {violation.found_value && (
            <span className="violation-found">
              Found: {violation.found_value}
            </span>
          )}
        </div>
      )}

      {violation.statutory_penalty && (
        <div style={{ marginTop: "8px", fontSize: "0.75rem", color: "#fca5a5", background: "rgba(225, 29, 72, 0.1)", padding: "6px 10px", borderRadius: "4px", border: "1px solid rgba(225, 29, 72, 0.2)" }}>
          <strong>Statutory Penalty:</strong> {violation.statutory_penalty}
        </div>
      )}

      {violation.is_discrepancy && (
        <motion.div
          style={{
            marginTop: "var(--space-sm)",
            padding: "var(--space-xs) var(--space-sm)",
            background: "rgba(244, 63, 94, 0.1)",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.75rem",
            color: "var(--accent-rose)",
            fontWeight: 600,
            display: "inline-block",
          }}
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 500 }}
        >
          ⚠️ CROSS-MODAL DISCREPANCY (Web Listing vs. Physical Package)
        </motion.div>
      )}
    </motion.div>
  );
}
