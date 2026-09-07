import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Globe,
  ShieldCheck,
  BarChart3,
  WifiOff,
  RotateCw,
  CheckCircle2,
  ScanLine,
  ImagePlus,
  Phone,
  Sparkles,
  ExternalLink,
  ShieldAlert,
  Scale,
} from "lucide-react";

import "./styles/globals.css";

import ImageUploader from "./components/ImageUploader";
import UrlAuditor from "./components/UrlAuditor";
import AuditReport from "./components/AuditReport";
import AnalyticsDashboard from "./components/AnalyticsDashboard";
import LiveScanner from "./components/LiveScanner";
import VerificationReport from "./components/VerificationReport";
import { auditImage, auditUrl } from "./api";
import type { AuditResponse } from "./api";
import { getFallbackAuditResult } from "./utils/demoData";
import {
  enqueueOfflineScan,
  getPendingScansCount,
  syncAllPendingScans,
} from "./utils/offlineQueue";
import { useLanguage } from "./context/LanguageContext";
import { playScanSuccessFeedback } from "./utils/hapticsAndSound";

type TabKey = "livescan" | "scanner" | "url" | "analytics";

/** Legal Metrology AI Emblem / Scale & Shield Brand Logo */
function LmpcBrandLogo() {
  return (
    <div
      style={{
        width: "44px",
        height: "44px",
        borderRadius: "8px",
        background: "linear-gradient(135deg, #003366 0%, #0b3b60 100%)",
        border: "1.5px solid #002244",
        boxShadow: "0 2px 8px rgba(0, 51, 102, 0.25)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
    >
      <Scale size={24} color="#ffffff" />
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("livescan");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [loadingStage, setLoadingStage] = useState("");

  // --- Accessibility & Language State ---
  const [fontSizeOffset, setFontSizeOffset] = useState<number>(0);
  const { lang, toggleLang, t } = useLanguage();

  // --- Offline Field Inspection State ---
  const [isOffline, setIsOffline] = useState<boolean>(!navigator.onLine);
  const [pendingScansCount, setPendingScansCount] = useState<number>(0);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [offlineNotice, setOfflineNotice] = useState<string | null>(null);

  useEffect(() => {
    const checkQueue = async () => {
      const count = await getPendingScansCount();
      setPendingScansCount(count);
    };

    checkQueue();

    const handleOnline = async () => {
      setIsOffline(false);
      const count = await getPendingScansCount();
      if (count > 0) {
        setIsSyncing(true);
        await syncAllPendingScans();
        const updated = await getPendingScansCount();
        setPendingScansCount(updated);
        setIsSyncing(false);
        setOfflineNotice("Offline field inspections synced to national database successfully.");
        setTimeout(() => setOfflineNotice(null), 5000);
      }
    };

    const handleOffline = () => {
      setIsOffline(true);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  /** Manual sync trigger for queued scans. */
  const handleManualSync = async () => {
    if (pendingScansCount === 0 || isSyncing) return;
    setIsSyncing(true);
    const { success } = await syncAllPendingScans();
    const updated = await getPendingScansCount();
    setPendingScansCount(updated);
    setIsSyncing(false);
    setOfflineNotice(`Synchronized ${success} inspection(s) successfully.`);
    setTimeout(() => setOfflineNotice(null), 5000);
  };

  /** Handle packaging image audit with offline fallback. */
  const handleImageAudit = async (file: File) => {
    setError(null);
    setResult(null);

    if (!navigator.onLine) {
      await enqueueOfflineScan(file, "Offline Market Inspection");
      const count = await getPendingScansCount();
      setPendingScansCount(count);
      setOfflineNotice(
        "Network offline. Packaging photo cached in local encrypted storage. Auto-syncing when online."
      );
      setTimeout(() => setOfflineNotice(null), 7000);
      return;
    }

    setIsLoading(true);
    setLoadingStage("Uploading evidence & running Gemini Multimodal OCR...");

    try {
      const res = await auditImage(file);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
    } finally {
      setIsLoading(false);
      setLoadingStage("");
    }
  };

  /** Handle e-commerce URL audit. */
  const handleUrlAudit = async (url: string) => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    setLoadingStage("Autonomous ScrapeGraphAI crawler scraping marketplace listing...");

    try {
      const res = await auditUrl(url);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
    } finally {
      setIsLoading(false);
      setLoadingStage("");
    }
  };

  /** Quick Test Demonstration Trigger (for Instant Teammate & Judge Showcase) */
  const handleQuickDemo = (sampleType: "compliant" | "violation" | "imported" | "honey") => {
    playScanSuccessFeedback();
    setError(null);
    setIsLoading(true);
    setLoadingStage("Synthesizing statutory LMPC multi-agent compliance evaluation...");

    setTimeout(() => {
      let res: AuditResponse;
      if (sampleType === "compliant") {
        res = getFallbackAuditResult("image", "Tata Tea Gold 500g");
      } else if (sampleType === "violation") {
        res = getFallbackAuditResult("image", "Royal Shahi Garam Masala (Violations)");
      } else if (sampleType === "imported") {
        res = getFallbackAuditResult("image", "Swiss Choco Crunch (Imported)");
      } else {
        res = getFallbackAuditResult("image", "Himalayan Raw Multi-Floral Honey");
      }

      setResult(res);
      setIsLoading(false);
      setLoadingStage("");
      if (activeTab === "analytics") {
        setActiveTab("scanner");
      }
    }, 600);
  };

  /** Reset audit state. */
  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{
        background: "var(--bg)",
        color: "var(--text)",
        fontSize: fontSizeOffset === 1 ? "1.05rem" : fontSizeOffset === -1 ? "0.9rem" : "1rem",
      }}
    >
      {/* 1. GovTech Accessibility & SIH Innovation Bar */}
      <div className="top-accessibility-bar">
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <span>🇮🇳 <strong>Smart India Hackathon</strong> | {t("topbar_sih_title")}</span>
          <span style={{ color: "var(--border)" }}>|</span>
          <span style={{ color: "var(--gov-gold)", fontWeight: 600 }}>{t("topbar_proposal")}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1.2rem" }}>
          <a
            href="tel:1915"
            style={{ display: "flex", alignItems: "center", gap: "0.35rem", color: "var(--gov-gold)" }}
            title="Statutory Helpline Reference"
          >
            <Phone size={13} />
            <span>{t("topbar_helpline")}</span>
          </a>
          <span style={{ color: "var(--border)" }}>|</span>

          {/* Accessibility Font Size Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <button
              onClick={() => setFontSizeOffset(-1)}
              style={{
                background: fontSizeOffset === -1 ? "rgba(255, 255, 255, 0.25)" : "transparent",
                color: "#ffffff",
                border: "1px solid rgba(255, 255, 255, 0.4)",
                borderRadius: "3px",
                padding: "1px 5px",
                cursor: "pointer",
                fontSize: "0.7rem",
              }}
              title="Decrease Font Size"
            >
              A-
            </button>
            <button
              onClick={() => setFontSizeOffset(0)}
              style={{
                background: fontSizeOffset === 0 ? "rgba(255, 255, 255, 0.25)" : "transparent",
                color: "#ffffff",
                border: "1px solid rgba(255, 255, 255, 0.4)",
                borderRadius: "3px",
                padding: "1px 5px",
                cursor: "pointer",
                fontSize: "0.7rem",
              }}
              title="Standard Font Size"
            >
              A
            </button>
            <button
              onClick={() => setFontSizeOffset(1)}
              style={{
                background: fontSizeOffset === 1 ? "rgba(255, 255, 255, 0.25)" : "transparent",
                color: "#ffffff",
                border: "1px solid rgba(255, 255, 255, 0.4)",
                borderRadius: "3px",
                padding: "1px 5px",
                cursor: "pointer",
                fontSize: "0.7rem",
              }}
              title="Increase Font Size"
            >
              A+
            </button>
          </div>

          <span style={{ color: "rgba(255, 255, 255, 0.4)" }}>|</span>
          <button
            onClick={toggleLang}
            style={{
              background: "rgba(255, 255, 255, 0.15)",
              color: "#ffffff",
              border: "1px solid rgba(255, 255, 255, 0.35)",
              borderRadius: "4px",
              padding: "2px 8px",
              cursor: "pointer",
              fontWeight: 700,
              fontSize: "0.76rem",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
            title="Switch Language / भाषा बदलें"
          >
            <span>🌐</span>
            <span>{lang === "en" ? "हिन्दी" : "English"}</span>
          </button>
        </div>
      </div>

      {/* 2. Indian National Tricolor Strip */}
      <div className="tricolor-strip" />

      {/* 3. GovTech Prototype Masthead */}
      <header className="app-header">
        <div className="masthead-inner">
          <div className="brand-section">
            <LmpcBrandLogo />
            <div className="brand-titles">
              <span className="brand-hindi">{t("masthead_dept")}</span>
              <span className="brand-english">{t("masthead_title")}</span>
              <span className="brand-sub">
                <span className="badge-sih">{t("masthead_prototype_badge")}</span>
                <span>•</span>
                <span>{t("masthead_proposal_sub")}</span>
              </span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <div className="officer-badge-box">
              <div className="name flex items-center gap-1.5 justify-end">
                <ShieldCheck size={14} className="text-sky-400" />
                <span>{t("auditor_cockpit")}</span>
              </div>
              <div className="dept">{t("sih_sandbox")}</div>
            </div>

            <div className="ai-status-pill">
              <div className="ai-pulse-dot" />
              <span>{isOffline ? t("ai_offline") : t("ai_active")}</span>
            </div>
          </div>
        </div>

        {/* 4. Statutory Tab Navigation */}
        <nav className="tab-nav-container" id="main-nav">
          <button
            className={`tab-btn ${activeTab === "livescan" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("livescan");
              handleReset();
            }}
            id="tab-livescan"
          >
            <ScanLine size={16} />
            {t("tab_livescan")}
          </button>
          <button
            className={`tab-btn ${activeTab === "scanner" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("scanner");
              handleReset();
            }}
            id="tab-scanner"
          >
            <ImagePlus size={16} />
            {t("tab_scanner")}
          </button>
          <button
            className={`tab-btn ${activeTab === "url" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("url");
              handleReset();
            }}
            id="tab-url"
          >
            <Globe size={16} />
            {t("tab_url")}
          </button>
          <button
            className={`tab-btn ${activeTab === "analytics" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("analytics");
              handleReset();
            }}
            id="tab-analytics"
          >
            <BarChart3 size={16} />
            {t("tab_analytics")}
          </button>
        </nav>
      </header>

      {/* 5. Interactive Demonstration Shelf (Instant One-Click Showcase) */}
      <div className="demo-shelf-bar">
        <div className="demo-shelf-label">
          <Sparkles size={14} />
          <span>{t("demo_shelf_label")}</span>
        </div>
        <div className="demo-chips-list">
          <button
            className="demo-chip compliant"
            onClick={() => handleQuickDemo("compliant")}
            title="Load fully compliant pre-packaged commodity test"
          >
            {t("demo_tata_tea")}
          </button>
          <button
            className="demo-chip violation"
            onClick={() => handleQuickDemo("violation")}
            title="Load test with missing USP, missing Country of Origin, and non-standard units"
          >
            {t("demo_garam_masala")}
          </button>
          <button
            className="demo-chip violation"
            onClick={() => handleQuickDemo("imported")}
            title="Load imported confectionery test missing Indian importer & origin disclosures"
          >
            {t("demo_choco_wafers")}
          </button>
          <button
            className="demo-chip compliant"
            onClick={() => handleQuickDemo("honey")}
            title="Load verified authentic commodity test"
          >
            {t("demo_honey")}
          </button>
        </div>
      </div>

      {/* 6. Offline Status Notification Banner */}
      {(isOffline || pendingScansCount > 0) && (
        <div className="offline-banner">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <WifiOff size={15} />
            <span>
              {isOffline ? t("low_conn_mode") : t("online_sync_active")} •{" "}
              <strong>{pendingScansCount}</strong> {t("inspections_queued")}
            </span>
          </div>
          <button
            className="offline-sync-btn flex items-center gap-1.5"
            onClick={handleManualSync}
            disabled={isSyncing || pendingScansCount === 0}
          >
            <RotateCw size={13} className={isSyncing ? "animate-spin" : ""} />
            {isSyncing ? t("syncing") : t("sync_to_db")}
          </button>
        </div>
      )}

      {/* Offline Success Banner */}
      {offlineNotice && (
        <div
          style={{
            background: "rgba(16, 185, 129, 0.12)",
            borderBottom: "1px solid rgba(16, 185, 129, 0.3)",
            color: "#34d399",
            padding: "0.6rem 1.5rem",
            fontSize: "0.85rem",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <CheckCircle2 size={16} />
          <span>{offlineNotice}</span>
        </div>
      )}

      {/* 7. Main Application Content Area */}
      <main className="app-main flex-1">
        {/* --- Analytics Tab --- */}
        {activeTab === "analytics" && (
          <motion.div
            key="analytics-view"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <AnalyticsDashboard />
          </motion.div>
        )}

        {/* --- Scanner, Upload & URL Tabs --- */}
        {activeTab !== "analytics" && (
          <AnimatePresence mode="wait">
            {/* Input Section */}
            {!result && !isLoading && (
              <motion.div
                key={`input-${activeTab}`}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.25 }}
              >
                {activeTab === "livescan" ? (
                  <div style={{ textAlign: "center", marginBottom: "32px" }}>
                    <div className="hero-badge">
                      <span>⚖️</span>
                      <span>{t("livescan_badge")}</span>
                    </div>
                    <motion.h2
                      className="hero-title"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                    >
                      {t("livescan_title")}
                    </motion.h2>
                    <p className="hero-subtitle">
                      {t("livescan_desc")}
                    </p>

                    {/* Telemetry Strip */}
                    <div className="telemetry-strip">
                      <div className="telemetry-item">
                        <span>🎯</span>
                        <span>{t("telemetry_vision")}</span>
                      </div>
                      <div className="telemetry-item">
                        <span>🛡️</span>
                        <span>{t("telemetry_fssai")}</span>
                      </div>
                      <div className="telemetry-item">
                        <span>🌐</span>
                        <span>{t("telemetry_registry")}</span>
                      </div>
                      <div className="telemetry-item">
                        <span>⚖️</span>
                        <span>{t("telemetry_penalties")}</span>
                      </div>
                    </div>

                    <LiveScanner
                      onScanComplete={(res) => setResult(res)}
                      onError={(msg) => setError(msg)}
                    />
                  </div>
                ) : activeTab === "scanner" ? (
                  <>
                    <div style={{ textAlign: "center", marginBottom: "32px" }}>
                      <div className="hero-badge">
                        <span>📸</span>
                        <span>{t("upload_badge")}</span>
                      </div>
                      <motion.h2
                        className="hero-title"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                      >
                        {t("upload_title")}
                      </motion.h2>
                      <p className="hero-subtitle">
                        {t("upload_desc")}
                      </p>

                      <div className="telemetry-strip">
                        <div className="telemetry-item">
                          <span>📋</span>
                          <span>{t("telemetry_10_decl")}</span>
                        </div>
                        <div className="telemetry-item">
                          <span>💰</span>
                          <span>{t("telemetry_usp_math")}</span>
                        </div>
                        <div className="telemetry-item">
                          <span>⚖️</span>
                          <span>{t("telemetry_s36")}</span>
                        </div>
                      </div>
                    </div>
                    <ImageUploader onFileSelect={handleImageAudit} isLoading={false} />
                  </>
                ) : (
                  <>
                    <div style={{ textAlign: "center", marginBottom: "32px" }}>
                      <div className="hero-badge">
                        <span>🛒</span>
                        <span>{t("url_badge")}</span>
                      </div>
                      <motion.h2
                        className="hero-title"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                      >
                        {t("url_title")}
                      </motion.h2>
                      <p className="hero-subtitle">
                        {t("url_desc")}
                      </p>
                    </div>
                    <UrlAuditor onSubmit={handleUrlAudit} isLoading={false} />
                  </>
                )}
              </motion.div>
            )}

            {/* --- Loading State --- */}
            {isLoading && (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="gov-card"
                style={{
                  minHeight: "360px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "3rem 2rem",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    width: "52px",
                    height: "52px",
                    border: "4px solid var(--border)",
                    borderTop: "4px solid var(--brand)",
                    borderRadius: "50%",
                    animation: "spin 1s linear infinite",
                    marginBottom: "1.5rem",
                  }}
                />
                <div style={{ fontWeight: 800, fontSize: "1.2rem", color: "#ffffff", marginBottom: "0.5rem" }}>
                  {loadingStage}
                </div>
                <div style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "2rem" }}>
                  Multi-agent statutory pipeline evaluating Legal Metrology Rules &amp; National Registries...
                </div>

                {/* Pipeline Progress */}
                <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap", justifyContent: "center" }}>
                  {[
                    { icon: "🛒", label: "Scraper Agent", active: activeTab === "url" },
                    { icon: "👁️", label: "Vision OCR", active: true },
                    { icon: "🏛️", label: "Legal Rule Engine", active: true },
                    { icon: "🛡️", label: "Fraud Verifier", active: true },
                    { icon: "📋", label: "Notice Generator", active: true },
                  ].map((step, i) => (
                    <motion.div
                      key={step.label}
                      style={{
                        textAlign: "center",
                        opacity: step.active ? 1 : 0.4,
                      }}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: step.active ? 1 : 0.4, y: 0 }}
                      transition={{ delay: i * 0.1 }}
                    >
                      <div style={{ fontSize: "1.6rem", marginBottom: "6px" }}>
                        {step.icon}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text)", fontWeight: 600 }}>
                        {step.label}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* --- Error State --- */}
            {error && !isLoading && (
              <motion.div
                key="error"
                className="gov-card"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  padding: "2.5rem 2rem",
                  borderLeft: "4px solid var(--danger)",
                  textAlign: "center",
                }}
              >
                <ShieldAlert size={48} className="text-red-500 mx-auto mb-3" />
                <h3 style={{ fontSize: "1.2rem", fontWeight: 800, color: "#ffffff", marginBottom: "0.5rem" }}>
                  Inspection Encountered An Issue
                </h3>
                <p style={{ color: "var(--muted)", fontSize: "0.9rem", maxWidth: "600px", margin: "0 auto 1.5rem" }}>
                  {error}
                </p>
                <button
                  className="btn-gov-secondary"
                  onClick={handleReset}
                >
                  Return to Scanner
                </button>
              </motion.div>
            )}

            {/* --- Results --- */}
            {result?.verdict && !isLoading && (
              <motion.div
                key="results"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4 }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "1.5rem",
                    flexWrap: "wrap",
                    gap: "12px",
                  }}
                >
                  <h2
                    style={{
                      fontSize: "1.3rem",
                      fontWeight: 800,
                      color: "#ffffff",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.5rem",
                    }}
                  >
                    <ShieldCheck size={24} style={{ color: "var(--brand)" }} />
                    Official Legal Metrology Inspection Notice
                    {result.platform && (
                      <span className="badge-pass">{result.platform}</span>
                    )}
                  </h2>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      className="btn-gov-secondary"
                      onClick={() => window.print()}
                      title="Print official notice"
                    >
                      🖨️ Print Notice
                    </button>
                    <button className="btn-gov-primary" onClick={handleReset}>
                      New Inspection
                    </button>
                  </div>
                </div>

                <AuditReport
                  verdict={result.verdict}
                  extractions={result.extractions}
                  listingData={result.listing_data}
                  platform={result.platform}
                  sourceUrl={result.source_url}
                />

                {result.verification && (
                  <div style={{ marginTop: "2.5rem" }}>
                    <h2
                      style={{
                        fontSize: "1.3rem",
                        fontWeight: 800,
                        color: "#ffffff",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        marginBottom: "1rem",
                      }}
                    >
                      <ShieldCheck size={24} style={{ color: "var(--brand)" }} />
                      Package Authenticity &amp; Counterfeit Verification
                    </h2>
                    <VerificationReport verification={result.verification} />
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </main>

      {/* 8. GovTech SIH26034 Prototype Footer */}
      <footer className="gov-footer">
        <div className="gov-footer-top">
          <div className="gov-footer-col">
            <div className="flex items-center gap-2 mb-2">
              <LmpcBrandLogo />
              <div>
                <div style={{ color: "#fff", fontWeight: 800, fontSize: "0.92rem", lineHeight: "1.2" }}>
                  LMPC Compliance Engine
                </div>
                <div style={{ color: "var(--brand)", fontSize: "0.72rem", fontWeight: 700 }}>
                  {t("footer_prototype_title")}
                </div>
              </div>
            </div>
            <p style={{ fontSize: "0.78rem", lineHeight: "1.6", color: "var(--muted)", maxWidth: "460px" }}>
              {t("footer_desc")}
            </p>
            <div style={{ marginTop: "12px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <span className="badge-pass">{t("masthead_prototype_badge")}</span>
              <span className="badge-pass">{t("badge_gigw")}</span>
              <span className="badge-pass">{t("badge_multiagent")}</span>
            </div>
          </div>

          <div className="gov-footer-col">
            <h4>{t("footer_portals_title")}</h4>
            <ul>
              <li>
                <a href="https://consumerhelpline.gov.in" target="_blank" rel="noreferrer" className="flex items-center gap-1">
                  National Consumer Helpline (1915) <ExternalLink size={11} />
                </a>
              </li>
              <li>
                <a href="https://edaakhil.nic.in" target="_blank" rel="noreferrer" className="flex items-center gap-1">
                  e-Daakhil Consumer Commission <ExternalLink size={11} />
                </a>
              </li>
              <li>
                <a href="https://bis.gov.in" target="_blank" rel="noreferrer" className="flex items-center gap-1">
                  Bureau of Indian Standards (BIS) <ExternalLink size={11} />
                </a>
              </li>
              <li>
                <a href="https://fssai.gov.in" target="_blank" rel="noreferrer" className="flex items-center gap-1">
                  FSSAI FoSCoS Portal <ExternalLink size={11} />
                </a>
              </li>
            </ul>
          </div>

          <div className="gov-footer-col">
            <h4>{t("footer_acts_title")}</h4>
            <ul>
              <li>
                <span className="text-xs text-slate-400">The Legal Metrology Act, 2009</span>
              </li>
              <li>
                <span className="text-xs text-slate-400">LM (Packaged Commodities) Rules, 2011</span>
              </li>
              <li>
                <span className="text-xs text-slate-400">2021 Unit Sale Price (USP) Amendment</span>
              </li>
              <li>
                <span className="text-xs text-slate-400">The Consumer Protection Act, 2019</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="gov-footer-bottom">
          <div>{t("footer_copy_left")}</div>
          <div>{t("footer_copy_right")}</div>
        </div>
      </footer>
    </div>
  );
}
