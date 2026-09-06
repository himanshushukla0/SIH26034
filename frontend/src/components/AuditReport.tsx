import { motion } from "framer-motion";
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  ShieldCheck,
  AlertTriangle,
  BarChart3,
  Printer,
} from "lucide-react";
import type { AuditVerdict, PackagingExtractions } from "../api";
import ComplianceGauge from "./ComplianceGauge";
import ViolationCard from "./ViolationCard";
import ComparisonView from "./ComparisonView";
import { useLanguage } from "../context/LanguageContext";

interface AuditReportProps {
  verdict: AuditVerdict;
  extractions?: PackagingExtractions;
  listingData?: Record<string, unknown>;
  platform?: string;
  sourceUrl?: string;
}

/** Map internal field keys to bilingual human-readable labels. */
const DECLARATION_LABELS: Record<string, { en: string; hi: string }> = {
  manufacturer_name: { en: "Manufacturer / Packer Name", hi: "निर्माता / पैकर का नाम" },
  manufacturer_address: { en: "Manufacturer Address", hi: "निर्माता / पैकर का पता" },
  country_of_origin: { en: "Country of Origin", hi: "मूल देश (Country of Origin)" },
  generic_name: { en: "Generic / Common Name", hi: "वस्तु का सामान्य / जेनेरिक नाम" },
  net_quantity: { en: "Net Quantity", hi: "शुद्ध मात्रा (Net Quantity)" },
  manufacture_date: { en: "Month & Year of Mfg/Packing", hi: "निर्माण / पैकिंग का माह एवं वर्ष" },
  expiry_date: { en: "Best Before / Expiry Date", hi: "उपयोग की अंतिम तिथि (Expiry Date)" },
  mrp: { en: "Maximum Retail Price (MRP)", hi: "अधिकतम खुदरा मूल्य (MRP)" },
  unit_sale_price: { en: "Unit Sale Price (USP)", hi: "प्रति इकाई विक्रय मूल्य (USP)" },
  consumer_care: { en: "Consumer Care Details", hi: "उपभोक्ता सहायता विवरण" },
};

function getStatusIcon(status: string) {
  switch (status) {
    case "FOUND":
      return <CheckCircle size={16} />;
    case "MISSING":
      return <XCircle size={16} />;
    case "PARTIAL":
      return <AlertCircle size={16} />;
    default:
      return <AlertCircle size={16} />;
  }
}

function getStatusClass(status: string): string {
  switch (status) {
    case "FOUND":
      return "found";
    case "MISSING":
      return "missing";
    case "PARTIAL":
      return "partial";
    default:
      return "partial";
  }
}

export default function AuditReport({
  verdict,
  extractions,
  listingData,
  platform,
  sourceUrl,
}: AuditReportProps) {
  const { lang, t } = useLanguage();
  const criticalCount = verdict.violations.filter(
    (v) => v.severity === "critical"
  ).length;
  const majorCount = verdict.violations.filter(
    (v) => v.severity === "major"
  ).length;
  const minorCount = verdict.violations.filter(
    (v) => v.severity === "minor"
  ).length;

  const handlePrint = () => {
    window.print();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* --- Ministry of Consumer Affairs Statutory Authority Banner --- */}
      <div
        className="glass-card"
        style={{
          padding: "var(--space-md) var(--space-lg)",
          marginBottom: "var(--space-lg)",
          borderLeft: "4px solid #38bdf8",
          background: "rgba(15, 23, 42, 0.6)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--space-sm)",
        }}
      >
        <div>
          <div style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "#38bdf8", fontWeight: 700 }}>
            {t("act_reference_subtitle")}
          </div>
          <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
            {t("statutory_audit_banner")}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
            {t("statutory_enforcement_sub")}
          </div>
        </div>
        <button
          onClick={handlePrint}
          className="btn-secondary"
          style={{ padding: "6px 14px", fontSize: "0.8rem", display: "flex", alignItems: "center", gap: "6px" }}
        >
          <Printer size={14} /> {t("print_notice_btn")}
        </button>
      </div>

      {/* --- Section 15 Manual Inspection Alert (if NEEDS_MANUAL_REVIEW) --- */}
      {verdict.overall_status === "NEEDS_MANUAL_REVIEW" && (
        <div
          className="glass-card"
          style={{
            padding: "var(--space-md) var(--space-lg)",
            marginBottom: "var(--space-lg)",
            borderLeft: "4px solid #f59e0b",
            background: "rgba(245, 158, 11, 0.08)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#fbbf24", fontWeight: 700, fontSize: "0.9rem" }}>
            <AlertTriangle size={18} />
            STATUTORY INSPECTION DIRECTIVE UNDER SECTION 15
          </div>
          <p style={{ margin: "6px 0 0 0", fontSize: "0.82rem", color: "#fde68a", lineHeight: 1.5 }}>
            The automated scan detected optical uncertainty (low OCR confidence, motion blur, or damaged label surface).
            Under <strong>Section 15 of the Legal Metrology Act, 2009</strong>, an authorized Legal Metrology Officer
            must conduct physical inspection of the pre-packaged commodity before issuing formal penalty summons.
          </p>
          {verdict.manual_review_reasons && verdict.manual_review_reasons.length > 0 && (
            <ul style={{ margin: "8px 0 0 16px", padding: 0, fontSize: "0.78rem", color: "#fef3c7" }}>
              {verdict.manual_review_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="results-grid">
        {/* --- Sidebar: Gauge + Stats --- */}
        <div className="results-sidebar">
          <div
            className="glass-card"
            style={{ padding: "var(--space-xl)", marginBottom: "var(--space-lg)" }}
          >
            <ComplianceGauge
              score={verdict.compliance_score}
              status={verdict.overall_status}
            />
          </div>

          {/* Summary Stats */}
          <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-sm)",
                marginBottom: "var(--space-md)",
                fontSize: "0.85rem",
                fontWeight: 600,
              }}
            >
              <BarChart3 size={16} style={{ color: "var(--accent-cyan)" }} />
              {lang === "hi" ? "ऑडिट सारांश" : "Audit Summary"}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.85rem",
                }}
              >
                <span style={{ color: "var(--text-muted)" }}>
                  {lang === "hi" ? "कुल जांच" : "Total Checks"}
                </span>
                <span style={{ fontWeight: 700 }}>{verdict.total_checks}</span>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.85rem",
                }}
              >
                <span style={{ color: "var(--accent-emerald)" }}>
                  {lang === "hi" ? "✓ सफल (Passed)" : "✓ Passed"}
                </span>
                <span style={{ fontWeight: 700, color: "var(--accent-emerald)" }}>
                  {verdict.passed_checks}
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.85rem",
                }}
              >
                <span style={{ color: "var(--accent-rose)" }}>
                  {lang === "hi" ? "✗ विफल (Failed)" : "✗ Failed"}
                </span>
                <span style={{ fontWeight: 700, color: "var(--accent-rose)" }}>
                  {verdict.failed_checks}
                </span>
              </div>

              <hr
                style={{
                  border: "none",
                  borderTop: "1px solid var(--border-subtle)",
                  margin: "var(--space-xs) 0",
                }}
              />

              {criticalCount > 0 && (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "0.8rem",
                  }}
                >
                  <span className="badge badge-critical" style={{ fontSize: "0.7rem" }}>
                    {t("severity_critical")}
                  </span>
                  <span style={{ fontWeight: 700 }}>{criticalCount}</span>
                </div>
              )}
              {majorCount > 0 && (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "0.8rem",
                  }}
                >
                  <span className="badge badge-major" style={{ fontSize: "0.7rem" }}>
                    {t("severity_major")}
                  </span>
                  <span style={{ fontWeight: 700 }}>{majorCount}</span>
                </div>
              )}
              {minorCount > 0 && (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "0.8rem",
                  }}
                >
                  <span className="badge badge-minor" style={{ fontSize: "0.7rem" }}>
                    {t("severity_minor")}
                  </span>
                  <span style={{ fontWeight: 700 }}>{minorCount}</span>
                </div>
              )}
            </div>

            {verdict.computed_usp && (
              <div
                style={{
                  marginTop: "var(--space-md)",
                  padding: "var(--space-sm) var(--space-md)",
                  background: "rgba(99, 102, 241, 0.1)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.8rem",
                }}
              >
                <span style={{ color: "var(--text-muted)" }}>{t("computed_usp_label")} </span>
                <span style={{ fontWeight: 700, color: "var(--text-accent)" }}>
                  {verdict.computed_usp}
                </span>
              </div>
            )}

            {/* Official Report Actions */}
            <div style={{ marginTop: "var(--space-lg)", display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
              <button
                className="btn btn-outline"
                onClick={handlePrint}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.5rem",
                  fontSize: "0.8rem",
                  padding: "0.6rem 0.8rem",
                  borderColor: "rgba(99, 102, 241, 0.4)",
                  color: "#a5b4fc",
                }}
              >
                <Printer size={14} />
                {t("print_notice_btn")}
              </button>
            </div>
          </div>
        </div>

        {/* --- Main Content: Declarations + Violations --- */}
        <div className="results-main">
          {/* Declaration Checklist */}
          <div>
            <div className="section-header">
              <h3 className="section-title">
                <ShieldCheck size={20} style={{ color: "var(--accent-emerald)" }} />
                {t("declarations_checklist_title")}
              </h3>
            </div>
            <div className="declaration-grid">
              {Object.entries(verdict.declaration_status).map(([key, decl], i) => (
                <motion.div
                  key={key}
                  className="declaration-item"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <div className={`declaration-icon ${getStatusClass(decl.status)}`}>
                    {getStatusIcon(decl.status)}
                  </div>
                  <div>
                    <div className="declaration-label">
                      {DECLARATION_LABELS[key]?.[lang] || DECLARATION_LABELS[key]?.en || key}
                    </div>
                    <div className="declaration-value">
                      {decl.value
                        ? String(decl.value)
                        : decl.status === "MISSING"
                        ? lang === "hi"
                          ? "पैकेज पर नहीं मिला"
                          : "Not found on package"
                        : lang === "hi"
                        ? "आंशिक रूप से पहचाना गया"
                        : "Partially detected"}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Violations */}
          {verdict.violations.length > 0 && (
            <div>
              <div className="section-header">
                <h3 className="section-title">
                  <AlertTriangle size={20} style={{ color: "var(--accent-amber)" }} />
                  {t("violations_section_title")} ({verdict.violations.length})
                </h3>
              </div>
              {verdict.violations.map((v, i) => (
                <ViolationCard key={`${v.rule_reference}-${i}`} violation={v} index={i} />
              ))}
            </div>
          )}

          {/* No Violations */}
          {verdict.violations.length === 0 && (
            <motion.div
              className="glass-card"
              style={{
                padding: "var(--space-2xl)",
                textAlign: "center",
              }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <CheckCircle
                size={48}
                style={{ color: "var(--accent-emerald)", marginBottom: "var(--space-md)" }}
              />
              <h3 style={{ fontSize: "1.125rem", marginBottom: "var(--space-sm)" }}>
                Fully Compliant
              </h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                All mandatory declarations under the Legal Metrology (Packaged
                Commodities) Rules, 2011 are present and correctly formatted.
              </p>
            </motion.div>
          )}
        </div>
      </div>

      {/* --- Cross-Modal E-Commerce Discrepancy Comparison --- */}
      {extractions && listingData && (
        <ComparisonView
          extractions={extractions}
          listingData={listingData}
          platform={platform}
          sourceUrl={sourceUrl}
          violations={verdict.violations}
        />
      )}
    </motion.div>
  );
}
