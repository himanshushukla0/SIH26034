import { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface ComplianceGaugeProps {
  score: number; // 0 — 100
  status: string; // "COMPLIANT" | "NON_COMPLIANT" | "PARTIAL_VIOLATION"
}

function getGaugeColor(score: number, status?: string): string {
  if (status === "NEEDS_MANUAL_REVIEW") return "#f59e0b"; // Amber
  if (score >= 90) return "#10b981"; // Emerald
  if (score >= 70) return "#22d3ee"; // Cyan
  if (score >= 50) return "#f59e0b"; // Amber
  if (score >= 30) return "#f97316"; // Orange
  return "#ef4444"; // Red
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "COMPLIANT":
      return "COMPLIANT";
    case "PARTIAL_VIOLATION":
      return "PARTIAL";
    case "NEEDS_MANUAL_REVIEW":
      return "MANUAL REVIEW (SEC 15)";
    case "NON_COMPLIANT":
      return "NON-COMPLIANT";
    default:
      return status;
  }
}

function getStatusBadgeClass(status: string): string {
  switch (status) {
    case "COMPLIANT":
      return "badge-compliant";
    case "PARTIAL_VIOLATION":
    case "NEEDS_MANUAL_REVIEW":
      return "badge-partial";
    case "NON_COMPLIANT":
      return "badge-violation";
    default:
      return "badge-partial";
  }
}

export default function ComplianceGauge({ score, status }: ComplianceGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  const radius = 85;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (animatedScore / 100) * circumference;
  const color = getGaugeColor(score, status);

  useEffect(() => {
    // Animate score from 0 to target
    const timer = setTimeout(() => setAnimatedScore(score), 100);
    return () => clearTimeout(timer);
  }, [score]);

  return (
    <motion.div
      className="gauge-container"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6, type: "spring" }}
    >
      <div className="gauge-ring">
        <svg viewBox="0 0 200 200">
          {/* Background ring */}
          <circle
            className="gauge-bg"
            cx="100"
            cy="100"
            r={radius}
          />
          {/* Animated fill ring */}
          <motion.circle
            className="gauge-fill"
            cx="100"
            cy="100"
            r={radius}
            stroke={color}
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.5, ease: "easeOut", delay: 0.3 }}
            style={{
              filter: `drop-shadow(0 0 8px ${color}40)`,
            }}
          />
        </svg>

        {/* Center score display */}
        <div className="gauge-score">
          <motion.span
            className="gauge-score-value"
            style={{ color }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            {Math.round(animatedScore)}%
          </motion.span>
          <span className="gauge-score-label">Compliance</span>
        </div>
      </div>

      {/* Status badge */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        <span className={`badge ${getStatusBadgeClass(status)}`}>
          {getStatusLabel(status)}
        </span>
      </motion.div>
    </motion.div>
  );
}
