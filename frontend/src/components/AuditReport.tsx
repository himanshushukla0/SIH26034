import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  ShieldCheck,
  AlertTriangle,
  BarChart3,
  Printer,
  Copy,
  Download,
  Scale,
  X,
  Layers,
  Zap,
  HelpCircle,
} from "lucide-react";
import {
  draftStatutoryNotice,
  type AuditVerdict,
  type PackagingExtractions,
  type StatutoryNoticeResult,
  type ShotMetadata,
  type Stage1Economics,
} from "../api";
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
  shotsMetadata?: ShotMetadata[];
  stage1Economics?: Stage1Economics;
  inputType?: string;
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
  shotsMetadata,
  stage1Economics,
  inputType,
}: AuditReportProps) {
  const { lang, t } = useLanguage();
  const [showNoticeModal, setShowNoticeModal] = useState(false);
  const [offenceNumber, setOffenceNumber] = useState(1);
  const [noticeResult, setNoticeResult] = useState<StatutoryNoticeResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [isDrafting, setIsDrafting] = useState(false);

  const criticalCount = verdict.violations.filter(
    (v) => v.severity === "critical"
  ).length;
  const majorCount = verdict.violations.filter(
    (v) => v.severity === "major"
  ).length;
  const minorCount = verdict.violations.filter(
    (v) => v.severity === "minor"
  ).length;

  const ruleMap: Record<string, string> = {
    manufacturer_name: "MANUFACTURER",
    manufacturer_address: "MANUFACTURER",
    country_of_origin: "COUNTRY_OF_ORIGIN",
    generic_name: "COMMODITY_NAME",
    net_quantity: "NET_QUANTITY",
    net_quantity_unit: "NET_QUANTITY",
    manufacture_date: "MFG_DATE",
    expiry_date: "EXPIRY_DATE",
    mrp: "MRP",
    unit_sale_price: "UNIT_SALE_PRICE",
    consumer_care: "CONSUMER_CARE",
    pdp_font_size: "PDP_AREA_FONT",
  };

  useEffect(() => {
    if (showNoticeModal) {
      setIsDrafting(true);
      const failures = verdict.violations.map((v) => ({
        rule_id: ruleMap[v.field_name] || "MANUFACTURER",
        found: v.found_value || v.description || "-",
        detail: v.description,
      }));

      const prodName =
        typeof extractions?.product_name?.value === "string"
          ? extractions.product_name.value
          : typeof extractions?.product_name === "string"
          ? extractions.product_name
          : undefined;
      const mfgName =
        typeof extractions?.manufacturer_name?.value === "string"
          ? extractions.manufacturer_name.value
          : typeof extractions?.manufacturer_name === "string"
          ? extractions.manufacturer_name
          : undefined;
      const bcode =
        typeof extractions?.barcode_number?.value === "string"
          ? extractions.barcode_number.value
          : typeof extractions?.barcode_number === "string"
          ? extractions.barcode_number
          : undefined;

      draftStatutoryNotice({
        item: {
          name: prodName || (listingData?.title as string) || "Pre-Packaged Commodity",
          manufacturer: mfgName || (listingData?.brand as string) || "Responsible Packer / Importer",
          barcode: bcode || "-",
          data_source: sourceUrl || "Vision OCR & Multimodal Compliance Engine (SIH26034)",
          checks: verdict.violations.map((v) => v.description),
        },
        failures,
        offence_number: offenceNumber,
        officer_name: "Inspector of Legal Metrology, Enforcement Division",
      })
        .then((res) => {
          setNoticeResult(res);
          setIsDrafting(false);
        })
        .catch((err) => {
          console.error(err);
          setIsDrafting(false);
        });
    }
  }, [showNoticeModal, offenceNumber, verdict, extractions, listingData, sourceUrl]);

  const handlePrint = () => {
    window.print();
  };

  const handleCopyNotice = () => {
    if (noticeResult?.text) {
      navigator.clipboard.writeText(noticeResult.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadNotice = () => {
    if (noticeResult?.text) {
      const blob = new Blob([noticeResult.text], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `LMPC_Statutory_Notice_${offenceNumber === 1 ? "Improvement_s15" : "ShowCause_s36"}.txt`;
      link.click();
      URL.revokeObjectURL(url);
    }
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
          border: "1px solid #bfdbfe",
          borderLeft: "4px solid var(--gov-navy)",
          background: "#eff6ff",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--space-sm)",
          borderRadius: "8px",
        }}
      >
        <div>
          <div style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--gov-navy)", fontWeight: 700 }}>
            {t("act_reference_subtitle")}
          </div>
          <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text)", marginTop: "2px" }}>
            {t("statutory_audit_banner")}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
            {t("statutory_enforcement_sub")}
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {verdict.violations.length > 0 && (
            <button
              onClick={() => setShowNoticeModal(true)}
              className="btn btn-primary"
              style={{
                padding: "6px 14px",
                fontSize: "0.8rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: "var(--gov-navy)",
                color: "#ffffff",
                borderColor: "var(--gov-navy)",
                boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
              }}
            >
              <Scale size={14} /> Draft Notice (s.15(6))
            </button>
          )}
          <button
            onClick={handlePrint}
            className="btn btn-outline"
            style={{
              padding: "6px 14px",
              fontSize: "0.8rem",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "#ffffff",
              color: "var(--gov-navy)",
              borderColor: "var(--gov-navy)",
            }}
          >
            <Printer size={14} /> {t("print_notice_btn")}
          </button>
        </div>
      </div>

      {/* --- Section 15 Manual Inspection Alert (if NEEDS_MANUAL_REVIEW) --- */}
      {verdict.overall_status === "NEEDS_MANUAL_REVIEW" && (
        <div
          className="glass-card"
          style={{
            padding: "var(--space-md) var(--space-lg)",
            marginBottom: "var(--space-lg)",
            border: "1px solid #fde68a",
            borderLeft: "4px solid #d97706",
            background: "#fffbeb",
            borderRadius: "8px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#92400e", fontWeight: 700, fontSize: "0.9rem" }}>
            <AlertTriangle size={18} color="#d97706" />
            STATUTORY INSPECTION DIRECTIVE UNDER SECTION 15
          </div>
          <p style={{ margin: "6px 0 0 0", fontSize: "0.82rem", color: "#78350f", lineHeight: 1.5 }}>
            The automated scan detected optical uncertainty (low OCR confidence, motion blur, or damaged label surface).
            Under <strong>Section 15 of the Legal Metrology Act, 2009</strong>, an authorized Legal Metrology Officer
            must conduct physical inspection of the pre-packaged commodity before issuing formal penalty summons.
          </p>
          {verdict.manual_review_reasons && verdict.manual_review_reasons.length > 0 && (
            <ul style={{ margin: "8px 0 0 16px", padding: 0, fontSize: "0.78rem", color: "#92400e" }}>
              {verdict.manual_review_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* --- Multi-Shot Packaging Unified Overview (if multi_shot) --- */}
      {(inputType === "multi_shot" || (shotsMetadata && shotsMetadata.length > 0)) && (
        <div
          className="glass-card"
          style={{
            padding: "1.25rem 1.5rem",
            marginBottom: "1.5rem",
            borderRadius: "10px",
            background: "rgba(15, 23, 42, 0.65)",
            border: "1px solid rgba(56, 189, 248, 0.3)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={20} color="#38bdf8" />
              <span style={{ fontWeight: 800, fontSize: "1rem", color: "#ffffff" }}>
                Multi-Shot Packaging Capture — Unified Label Analysis
              </span>
              <span
                style={{
                  fontSize: "0.72rem",
                  padding: "2px 8px",
                  borderRadius: "4px",
                  background: "rgba(56, 189, 248, 0.15)",
                  color: "#38bdf8",
                  fontWeight: 700,
                  border: "1px solid rgba(56, 189, 248, 0.35)",
                }}
              >
                {shotsMetadata?.length || 2} Panels Unified
              </span>
            </div>
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              Fused into 1 Legal Metrology Entity
            </span>
          </div>

          {/* Panel breakdown cards */}
          {shotsMetadata && shotsMetadata.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.75rem", marginBottom: "1rem" }}>
              {shotsMetadata.map((shot, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "0.85rem",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.82rem", color: "#ffffff", textTransform: "capitalize" }}>
                      Panel {idx + 1}: {shot.panel === "front" ? "Front PDP" : shot.panel === "back" ? "Back Declarations" : "Barcode / Sticker"}
                    </span>
                    <span style={{ fontSize: "0.68rem", color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
                      {shot.lines_count} lines
                    </span>
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                    {shot.description}
                  </div>
                  {shot.text_preview && (
                    <div style={{ fontSize: "0.68rem", color: "#38bdf8", fontFamily: "var(--font-mono)", background: "rgba(0,0,0,0.25)", padding: "4px 6px", borderRadius: "4px" }}>
                      "{shot.text_preview}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Stage 1 Screener Economics metrics */}
          <div
            style={{
              padding: "0.85rem 1rem",
              borderRadius: "8px",
              background: "rgba(16, 185, 129, 0.08)",
              border: "1px solid rgba(16, 185, 129, 0.25)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Zap size={18} color="#10b981" />
              <div>
                <div style={{ fontWeight: 700, fontSize: "0.82rem", color: "#10b981" }}>
                  Stage 1 Microsecond Screener Economics: ₹0.00 API Spend
                </div>
                <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
                  {stage1Economics?.needs_model === false
                    ? `Clean packaging coverage (${stage1Economics.coverage_percent}%) settled at Stage 1 without vision model.`
                    : "Low coverage or deficient declarations flagged for officer review."}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              <span
                style={{
                  fontSize: "0.72rem",
                  padding: "3px 8px",
                  borderRadius: "4px",
                  background: "rgba(16, 185, 129, 0.15)",
                  color: "#10b981",
                  fontWeight: 700,
                  fontFamily: "var(--font-mono)",
                }}
              >
                ⚡ {stage1Economics?.latency_ms || 1.8} ms
              </span>
              <span
                style={{
                  fontSize: "0.72rem",
                  padding: "3px 8px",
                  borderRadius: "4px",
                  background: "rgba(56, 189, 248, 0.15)",
                  color: "#38bdf8",
                  fontWeight: 700,
                }}
              >
                Coverage: {stage1Economics?.coverage_percent || verdict.compliance_score}%
              </span>
              {stage1Economics?.pin_code_detected && (
                <span
                  style={{
                    fontSize: "0.72rem",
                    padding: "3px 8px",
                    borderRadius: "4px",
                    background: "rgba(168, 85, 247, 0.15)",
                    color: "#c084fc",
                    fontWeight: 700,
                  }}
                >
                  PIN: {stage1Economics.pin_code || "Detected"}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --- Statutory Discipline: GENERIC_NAME Notice (if INSUFFICIENT_DATA) --- */}
      {verdict.overall_status === "INSUFFICIENT_DATA" && (
        <div
          className="glass-card"
          style={{
            padding: "1rem 1.25rem",
            marginBottom: "1.5rem",
            border: "1px solid #818cf8",
            borderLeft: "4px solid #6366f1",
            background: "rgba(99, 102, 241, 0.08)",
            borderRadius: "8px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#a5b4fc", fontWeight: 700, fontSize: "0.88rem" }}>
            <HelpCircle size={18} color="#818cf8" />
            STATUTORY DISCIPLINE: GENERIC_NAME DELIBERATELY UNPARSED BY REGEX
          </div>
          <p style={{ margin: "6px 0 0 0", fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            Indian packaging phrasing has no keyword anchor for generic commodity name — it is typically just the headline descriptive line.
            To enforce <strong>zero hallucination</strong>, the Stage 1 regex parser leaves GENERIC_NAME unparsed,
            capping clean labels at <strong>89% coverage</strong> and reporting <strong>INSUFFICIENT_DATA</strong> rather than COMPLIANT
            until confirmed by vision model or an inspecting officer.
          </p>
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
                  background: "#eff6ff",
                  border: "1px solid #bfdbfe",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.8rem",
                }}
              >
                <span style={{ color: "var(--text-muted)" }}>{t("computed_usp_label")} </span>
                <span style={{ fontWeight: 700, color: "var(--gov-navy)" }}>
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
                  borderColor: "var(--gov-navy)",
                  color: "var(--gov-navy)",
                  background: "#ffffff",
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
                    <div className="declaration-label" style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                      <span>{DECLARATION_LABELS[key]?.[lang] || DECLARATION_LABELS[key]?.en || key}</span>
                      {(decl as any).stitched && (
                        <span
                          style={{
                            fontSize: "0.65rem",
                            padding: "1px 5px",
                            borderRadius: "3px",
                            background: "rgba(217, 119, 6, 0.15)",
                            color: "#d97706",
                            border: "1px solid rgba(217, 119, 6, 0.3)",
                            fontWeight: 700,
                          }}
                          title="Extracted via Pass 2 adjacent line-pair stitching (Confidence: 0.82)"
                        >
                          🔗 Stitched Line
                        </span>
                      )}
                      {key === "generic_name" && decl.status === "PARTIAL" && (
                        <span
                          style={{
                            fontSize: "0.65rem",
                            padding: "1px 5px",
                            borderRadius: "3px",
                            background: "rgba(99, 102, 241, 0.15)",
                            color: "#818cf8",
                            border: "1px solid rgba(99, 102, 241, 0.3)",
                            fontWeight: 700,
                          }}
                          title="Unparsed by regex to prevent hallucination — requires vision model or officer confirmation"
                        >
                          ℹ️ Unanchored
                        </span>
                      )}
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

      {/* --- Statutory Notice Modal (Jan Vishwas Act, 2026 s.15(6)) --- */}
      {showNoticeModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(15, 23, 42, 0.65)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
          onClick={() => setShowNoticeModal(false)}
        >
          <div
            style={{
              background: "#ffffff",
              color: "#0f172a",
              borderRadius: "12px",
              width: "100%",
              maxWidth: "880px",
              maxHeight: "90vh",
              display: "flex",
              flexDirection: "column",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
              border: "1px solid #cbd5e1",
              overflow: "hidden",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid #e2e8f0",
                background: "#f8fafc",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Scale size={22} style={{ color: "var(--gov-navy)" }} />
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700, color: "var(--gov-navy)" }}>
                    Statutory Notice Drafting Engine
                  </h3>
                  <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                    Jan Vishwas (Amendment of Provisions) Act, 2026 • Legal Metrology Act, 2009
                  </span>
                </div>
              </div>
              <button
                onClick={() => setShowNoticeModal(false)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#64748b",
                  padding: "4px",
                  borderRadius: "6px",
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Offence & Instrument Selector Toolbar */}
            <div
              style={{
                padding: "12px 20px",
                background: "#eff6ff",
                borderBottom: "1px solid #bfdbfe",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "12px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#1e3a8a" }}>
                  Enforcement Level:
                </span>
                <div style={{ display: "flex", borderRadius: "6px", overflow: "hidden", border: "1px solid #93c5fd" }}>
                  <button
                    onClick={() => setOffenceNumber(1)}
                    style={{
                      padding: "5px 12px",
                      fontSize: "0.8rem",
                      fontWeight: offenceNumber === 1 ? 700 : 500,
                      background: offenceNumber === 1 ? "#1d4ed8" : "#ffffff",
                      color: offenceNumber === 1 ? "#ffffff" : "#1e3a8a",
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    1st Contravention (s.15(6) Improvement Notice)
                  </button>
                  <button
                    onClick={() => setOffenceNumber(2)}
                    style={{
                      padding: "5px 12px",
                      fontSize: "0.8rem",
                      fontWeight: offenceNumber >= 2 ? 700 : 500,
                      background: offenceNumber >= 2 ? "#b91c1c" : "#ffffff",
                      color: offenceNumber >= 2 ? "#ffffff" : "#991b1b",
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    Repeat Contravention (Show Cause Notice)
                  </button>
                </div>
              </div>

              {noticeResult && (
                <span
                  style={{
                    padding: "4px 12px",
                    borderRadius: "9999px",
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    letterSpacing: "0.04em",
                    background: noticeResult.instrument === "IMPROVEMENT_NOTICE" ? "#dbeafe" : "#fee2e2",
                    color: noticeResult.instrument === "IMPROVEMENT_NOTICE" ? "#1e40af" : "#991b1b",
                    border: `1px solid ${noticeResult.instrument === "IMPROVEMENT_NOTICE" ? "#93c5fd" : "#fca5a5"}`,
                  }}
                >
                  {noticeResult.instrument === "IMPROVEMENT_NOTICE" ? "⚖️ STATUTORY IMPROVEMENT NOTICE" : "⚠️ SHOW CAUSE NOTICE"}
                </span>
              )}
            </div>

            {/* Legal Rationale Callout */}
            {noticeResult?.reason && (
              <div
                style={{
                  margin: "12px 20px 0 20px",
                  padding: "10px 14px",
                  background: "#f8fafc",
                  borderLeft: "4px solid #3b82f6",
                  borderRadius: "4px",
                  fontSize: "0.8rem",
                  color: "#334155",
                  lineHeight: 1.4,
                }}
              >
                <strong>Legal Rationale:</strong> {noticeResult.reason}
              </div>
            )}

            {/* Notice Body Text Box */}
            <div style={{ padding: "12px 20px", flex: 1, overflowY: "auto" }}>
              {isDrafting ? (
                <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
                  Drafting statutory notice from LMPC rule table...
                </div>
              ) : (
                <pre
                  style={{
                    background: "#0f172a",
                    color: "#f8fafc",
                    padding: "16px",
                    borderRadius: "8px",
                    fontFamily: "'JetBrains Mono', 'Consolas', monospace",
                    fontSize: "0.78rem",
                    lineHeight: 1.45,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    maxHeight: "420px",
                    overflowY: "auto",
                    margin: 0,
                    border: "1px solid #334155",
                  }}
                >
                  {noticeResult?.text || "No notice generated."}
                </pre>
              )}
            </div>

            {/* Modal Actions Footer */}
            <div
              style={{
                padding: "12px 20px",
                borderTop: "1px solid #e2e8f0",
                background: "#f8fafc",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span style={{ fontSize: "0.72rem", color: "#64748b" }}>
                Decision-support draft under s.15(6). Must be signed by an authorized Inspector before service.
              </span>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  onClick={handleCopyNotice}
                  className="btn btn-outline"
                  style={{
                    padding: "6px 12px",
                    fontSize: "0.8rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "#ffffff",
                    color: "#0f172a",
                  }}
                >
                  <Copy size={14} /> {copied ? "Copied!" : "Copy Text"}
                </button>
                <button
                  onClick={handleDownloadNotice}
                  className="btn btn-primary"
                  style={{
                    padding: "6px 14px",
                    fontSize: "0.8rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "var(--gov-navy)",
                    color: "#ffffff",
                  }}
                >
                  <Download size={14} /> Download (.TXT)
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
