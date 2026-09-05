import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Globe,
  ShieldCheck,
  Activity,
  BarChart3,
  WifiOff,
  RotateCw,
  CheckCircle2,
  ScanLine,
  ImagePlus,
  Phone,
  Landmark,
  UserCheck,
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
import {
  enqueueOfflineScan,
  getPendingScansCount,
  syncAllPendingScans,
} from "./utils/offlineQueue";

type TabKey = "livescan" | "scanner" | "url" | "analytics";

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("livescan");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [loadingStage, setLoadingStage] = useState("");

  // --- Offline Field Inspection State ---
  const [isOffline, setIsOffline] = useState<boolean>(!navigator.onLine);
  const [pendingScansCount, setPendingScansCount] = useState<number>(0);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [offlineNotice, setOfflineNotice] = useState<string | null>(null);

  // Refresh pending count on mount & listen to connectivity
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
        setOfflineNotice("Offline field inspections synced to government database successfully.");
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

    // If offline, store locally in IndexedDB queue
    if (!navigator.onLine) {
      await enqueueOfflineScan(file, "Offline Market Inspection");
      const count = await getPendingScansCount();
      setPendingScansCount(count);
      setOfflineNotice(
        "Network connection offline. Packaging photo has been encrypted & cached locally. It will auto-sync when network resumes."
      );
      setTimeout(() => setOfflineNotice(null), 7000);
      return;
    }

    setIsLoading(true);
    setLoadingStage("Uploading image & running Gemini Vision OCR...");

    try {
      const res = await auditImage(file);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      if (msg.toLowerCase().includes("failed to fetch") || msg.toLowerCase().includes("network")) {
        await enqueueOfflineScan(file, "Offline Market Inspection (Fallback)");
        const count = await getPendingScansCount();
        setPendingScansCount(count);
        setOfflineNotice("Network lost during audit. Inspection saved to offline queue for later sync.");
      } else {
        setError(msg);
      }
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
    setLoadingStage("Crawling marketplace listing with ScrapeGraphAI...");

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

  /** Reset audit state. */
  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f4f6f9]">
      {/* 1. Official National Accessibility Strip */}
      <div className="top-accessibility-bar">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span>🇮🇳 <strong>भारत सरकार</strong> | Government of India</span>
          <span style={{ color: "#cbd5e1" }}>|</span>
          <span>National Legal Metrology Enforcement Portal</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <Phone size={13} style={{ color: "var(--gov-navy-primary)" }} /> National Consumer Helpline: <strong>1915</strong>
          </span>
          <span style={{ color: "#cbd5e1" }}>|</span>
          <span style={{ cursor: "pointer", fontWeight: 700, color: "var(--gov-navy-primary)" }}>हिन्दी</span>
        </div>
      </div>
      <div className="tricolor-strip" />

      {/* 2. Official Ministry Masthead */}
      <header className="app-header">
        <div className="masthead-inner">
          <div className="app-logo">
            <div className="app-logo-icon">
              <Landmark size={24} color="#0b3b60" />
            </div>
            <div>
              <h1>Department of Consumer Affairs</h1>
              <div className="subtitle">
                MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION • LEGAL METROLOGY DIVISION
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <div className="officer-badge-box">
              <div className="name flex items-center gap-1.5 justify-end">
                <UserCheck size={14} /> Legal Metrology Inspector
              </div>
              <div className="dept">Enforcement Cell • SIH26034</div>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
                padding: "0.35rem 0.75rem",
                borderRadius: "var(--radius-sm)",
                background: isOffline ? "#fffbeb" : "#f0fdf4",
                border: isOffline ? "1px solid #fde68a" : "1px solid #bbf7d0",
                fontSize: "0.75rem",
                fontFamily: "var(--font-mono)",
                fontWeight: 600,
                color: isOffline ? "#b45309" : "#15803d",
              }}
            >
              <Activity
                size={13}
                style={{
                  color: isOffline ? "#b45309" : "#15803d",
                }}
              />
              <span>{isOffline ? "OFFLINE CACHE" : "AI ENGINE ACTIVE"}</span>
            </div>
          </div>
        </div>

        {/* 3. Statutory Tab Navigation */}
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
            Field Camera Scanner
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
            Evidence Image Upload
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
            E-Commerce URL Auditor
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
            Officer MIS & Seizures
          </button>
        </nav>
      </header>

      {/* ========== Offline Status Notification Banner ========== */}
      {(isOffline || pendingScansCount > 0) && (
        <div className="offline-banner">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <WifiOff size={15} />
            <span>
              {isOffline ? "📡 Low Connectivity Field Mode" : "🌐 Online Sync"} •{" "}
              <strong>{pendingScansCount}</strong> inspection(s) queued in local encrypted storage
            </span>
          </div>
          <button
            className="offline-sync-btn flex items-center gap-1.5"
            onClick={handleManualSync}
            disabled={isSyncing || pendingScansCount === 0}
          >
            <RotateCw size={13} className={isSyncing ? "animate-spin" : ""} />
            {isSyncing ? "Syncing..." : "Sync to National DB"}
          </button>
        </div>
      )}

      {/* Offline Success Banner */}
      {offlineNotice && (
        <div
          style={{
            background: "#f0fdf4",
            borderBottom: "1px solid #bbf7d0",
            color: "#15803d",
            padding: "0.5rem 1.5rem",
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

      {/* ========== Main Content ========== */}
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

        {/* --- Scanner & URL Tabs --- */}
        {activeTab !== "analytics" && (
          <AnimatePresence mode="wait">
            {/* --- Input Section --- */}
            {!result && !isLoading && (
              <motion.div
                key={`input-${activeTab}`}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.25 }}
              >
                {activeTab === "livescan" ? (
                  <div style={{ textAlign: "center", marginBottom: "var(--space-xl)" }}>
                    <div className="hero-badge">
                      <span>⚖️</span>
                      <span>LEGAL METROLOGY ACT, 2009 • SECTION 15 STATUTORY ENFORCEMENT</span>
                    </div>
                    <motion.h2
                      className="hero-title"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                    >
                      Real-Time Packaging Authenticity & Statutory Scanner
                    </motion.h2>
                    <p className="hero-subtitle">
                      Point device camera at any pre-packaged commodity. Multi-agent OCR decodes barcodes,
                      verifies FSSAI 14-digit licenses, inspects expiry integrity, and cross-checks mandatory Rule 6 declarations.
                    </p>

                    {/* Telemetry Strip */}
                    <div className="telemetry-strip">
                      <div className="telemetry-item">
                        <span>🎯</span>
                        <span>Vision: <strong>Gemini Multimodal OCR</strong></span>
                      </div>
                      <div className="telemetry-item">
                        <span>🛡️</span>
                        <span>FSSAI: <strong>14-Digit FoSCoS Validator</strong></span>
                      </div>
                      <div className="telemetry-item">
                        <span>🌐</span>
                        <span>Registry: <strong>GS1 India DataKart</strong></span>
                      </div>
                      <div className="telemetry-item">
                        <span>⚖️</span>
                        <span>Penalties: <strong>Section 36 Compliance</strong></span>
                      </div>
                    </div>

                    <LiveScanner
                      onScanComplete={(res) => setResult(res)}
                      onError={(msg) => setError(msg)}
                    />
                  </div>
                ) : activeTab === "scanner" ? (
                  <>
                    <div style={{ textAlign: "center", marginBottom: "var(--space-xl)" }}>
                      <div className="hero-badge">
                        <span>📸</span>
                        <span>RULE 6(1) STATUTORY AUDITOR • MULTIMODAL OCR</span>
                      </div>
                      <motion.h2
                        className="hero-title"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                      >
                        Statutory Packaging Label Inspection
                      </motion.h2>
                      <p className="hero-subtitle">
                        Capture or upload packaging labels during market inspections. Multi-agent OCR audits all mandatory
                        declarations, checks Unit Sale Price (USP) math, and generates court-ready statutory notices.
                      </p>

                      <div className="telemetry-strip">
                        <div className="telemetry-item">
                          <span>📋</span>
                          <span>Mandatory: <strong>10 Declarations</strong></span>
                        </div>
                        <div className="telemetry-item">
                          <span>💰</span>
                          <span>Unit Price: <strong>Rule 6(11) Math</strong></span>
                        </div>
                        <div className="telemetry-item">
                          <span>⚖️</span>
                          <span>Penalties: <strong>Section 36 Ready</strong></span>
                        </div>
                      </div>
                    </div>
                    <ImageUploader onFileSelect={handleImageAudit} isLoading={false} />
                  </>
                ) : (
                  <>
                    <div style={{ textAlign: "center", marginBottom: "var(--space-xl)" }}>
                      <div className="hero-badge">
                        <span>🛒</span>
                        <span>E-COMMERCE DISCREPANCY AUDITOR • RULE 6(10) ENFORCEMENT</span>
                      </div>
                      <motion.h2
                        className="hero-title"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                      >
                        Marketplace Listing & Packaging Auditor
                      </motion.h2>
                      <p className="hero-subtitle">
                        Audit product listings on Amazon, Flipkart, Blinkit, Zepto, and Swiggy Instamart.
                        Scrapes structured schema and cross-verifies digital disclosures against physical packaging requirements.
                      </p>

                      <div className="telemetry-strip">
                        <div className="telemetry-item">
                          <span>🏪</span>
                          <span>Platforms: <strong>Amazon, Blinkit, Zepto, Flipkart</strong></span>
                        </div>
                        <div className="telemetry-item">
                          <span>🔍</span>
                          <span>Audit: <strong>Digital vs Physical Discrepancy</strong></span>
                        </div>
                      </div>
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
                  minHeight: "340px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "2rem",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    border: "4px solid #e2e8f0",
                    borderTop: "4px solid var(--gov-navy-primary)",
                    borderRadius: "50%",
                    animation: "spin 1s linear infinite",
                    marginBottom: "1.25rem",
                  }}
                />
                <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--gov-navy-dark)", marginBottom: "0.25rem" }}>
                  {loadingStage}
                </div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1.5rem" }}>
                  Multi-agent statutory pipeline evaluating Legal Metrology Rules & National Registries...
                </div>

                {/* Pipeline Progress */}
                <div style={{ display: "flex", gap: "1.5rem" }}>
                  {[
                    { icon: "🛒", label: "Scraper", active: activeTab === "url" },
                    { icon: "👁️", label: "Vision OCR", active: true },
                    { icon: "🏛️", label: "Legal Auditor", active: true },
                    { icon: "🛡️", label: "Verifier", active: true },
                    { icon: "📋", label: "Notice Gen", active: true },
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
                      <div style={{ fontSize: "1.5rem", marginBottom: "4px" }}>
                        {step.icon}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>
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
                  padding: "2rem",
                  borderLeft: "4px solid var(--gov-red)",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>⚠️</div>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--gov-red)", marginBottom: "0.5rem" }}>
                  Audit Execution Failed
                </h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", maxWidth: "600px", margin: "0 auto 1.25rem" }}>
                  {error}
                </p>
                <button
                  className="btn-gov-secondary"
                  onClick={handleReset}
                >
                  Try Again
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
                    marginBottom: "1.25rem",
                  }}
                >
                  <h2
                    style={{
                      fontSize: "1.25rem",
                      fontWeight: 700,
                      color: "var(--gov-navy-dark)",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.5rem",
                    }}
                  >
                    <ShieldCheck size={22} style={{ color: "var(--gov-navy-primary)" }} />
                    Official Legal Metrology Inspection Notice
                    {result.platform && (
                      <span className="badge-pass">{result.platform}</span>
                    )}
                  </h2>
                  <button className="btn-gov-secondary" onClick={handleReset}>
                    New Inspection
                  </button>
                </div>

                <AuditReport
                  verdict={result.verdict}
                  extractions={result.extractions}
                  listingData={result.listing_data}
                  platform={result.platform}
                  sourceUrl={result.source_url}
                />

                {result.verification && (
                  <div style={{ marginTop: "2rem" }}>
                    <h2
                      style={{
                        fontSize: "1.25rem",
                        fontWeight: 700,
                        color: "var(--gov-navy-dark)",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        marginBottom: "1rem",
                      }}
                    >
                      <ShieldCheck size={22} style={{ color: "var(--gov-navy-primary)" }} />
                      Package Authenticity Verification
                    </h2>
                    <VerificationReport verification={result.verification} />
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </main>

      {/* ========== Footer ========== */}
      <footer
        style={{
          textAlign: "center",
          padding: "1.5rem",
          color: "var(--text-muted)",
          fontSize: "0.78rem",
          background: "#ffffff",
          borderTop: "1px solid var(--border-card)",
          marginTop: "3rem",
        }}
      >
        SIH26034 • Legal Metrology (Packaged Commodities) Rules, 2011 •
        Ministry of Consumer Affairs, Food & Public Distribution •
        Department of Consumer Affairs, Government of India
      </footer>
    </div>
  );
}
