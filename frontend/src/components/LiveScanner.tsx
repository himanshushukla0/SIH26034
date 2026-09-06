/**
 * SIH26034 — Live Camera Barcode Scanner & Statutory Verification Cockpit
 * Department of Consumer Affairs • Government of India
 *
 * Real-time package scanning using the device camera with
 * html5-qrcode for barcode/QR detection, interactive reference
 * demo products, manual barcode lookup, and statutory telemetry.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Camera,
  CameraOff,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Loader2,
  Barcode,
  Search,
  Crosshair,
  Radio,
  CheckCircle2,
} from "lucide-react";
import { Html5Qrcode } from "html5-qrcode";
import { scanPackage } from "../api";
import type { AuditResponse } from "../api";
import { useLanguage } from "../context/LanguageContext";
import { playScanSuccessFeedback } from "../utils/hapticsAndSound";

interface LiveScannerProps {
  onScanComplete: (result: AuditResponse) => void;
  onError: (error: string) => void;
}

/** Pre-configured representative market samples for one-click verification demonstration. */
const DEMO_PRODUCTS = [
  {
    name: "Tata Tea Gold 500g",
    barcode: "8901030383478",
    badge: "COMPLIANT",
    color: "#15803d",
    desc: "Indian EAN-13 • Valid FoSCoS License • 100% Rule 6 Compliant",
    icon: "🍵",
  },
  {
    name: "Masala Spice Pouch",
    barcode: "8909999999999",
    badge: "INVALID FSSAI",
    color: "#b91c1c",
    desc: "Invalid State Lic. Code '00' • Notice under Section 36",
    icon: "🥫",
  },
  {
    name: "Swiss Cocoa Crunch",
    barcode: "7613035678901",
    badge: "ORIGIN DISCREPANCY",
    color: "#d97706",
    desc: "Imported Commodity • Missing Indian Importer / MRP Details",
    icon: "🍫",
  },
  {
    name: "Amul Pure Ghee 1L",
    barcode: "8901262010053",
    badge: "GS1 VERIFIED",
    color: "#0b3b60",
    desc: "GS1 DataKart Verified • Rule 6(11) Unit Sale Price Compliant",
    icon: "🥛",
  },
];

export default function LiveScanner({ onScanComplete, onError }: LiveScannerProps) {
  const { lang, t } = useLanguage();
  const [isScanning, setIsScanning] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastBarcode, setLastBarcode] = useState<string | null>(null);
  const [manualInput, setManualInput] = useState("");
  const [scanStatus, setScanStatus] = useState<"idle" | "scanning" | "detected" | "processing" | "success" | "error">("idle");
  const [processingStage, setProcessingStage] = useState("");
  const [cameraError, setCameraError] = useState<string | null>(null);

  const scannerRef = useRef<Html5Qrcode | null>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const processingLockRef = useRef(false);

  const SCANNER_ELEMENT_ID = "lmpc-barcode-scanner";

  /** Run complete verification on a given barcode string. */
  const runVerification = useCallback(
    async (barcode: string, imageBlob?: Blob) => {
      try {
        setIsProcessing(true);
        setScanStatus("processing");
        setLastBarcode(barcode);
        setProcessingStage("Connecting to Multi-Agent Statutory Pipeline...");
        await new Promise((r) => setTimeout(r, 400));

        setProcessingStage("Querying GS1 India DataKart & Open Food Facts...");
        await new Promise((r) => setTimeout(r, 350));

        setProcessingStage("Validating FSSAI 14-Digit FoSCoS License...");
        await new Promise((r) => setTimeout(r, 350));

        setProcessingStage("Evaluating Legal Metrology Act, 2009 Rule 6 Declarations...");

        const blobToSend = imageBlob || new Blob([], { type: "image/jpeg" });
        const auditResult = await scanPackage(blobToSend, barcode);

        setScanStatus("success");
        onScanComplete(auditResult);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setScanStatus("error");
        onError(msg || "Failed to complete statutory verification.");
      } finally {
        setIsProcessing(false);
        processingLockRef.current = false;
      }
    },
    [onScanComplete, onError]
  );

  /** Initialize camera and start barcode stream. */
  const startScanner = useCallback(async () => {
    setCameraError(null);
    setScanStatus("scanning");
    processingLockRef.current = false;

    try {
      if (scannerRef.current) {
        try {
          await scannerRef.current.stop();
        } catch {
          // Ignore
        }
      }

      const scanner = new Html5Qrcode(SCANNER_ELEMENT_ID);
      scannerRef.current = scanner;

      await scanner.start(
        { facingMode: "environment" },
        {
          fps: 15,
          qrbox: { width: 280, height: 200 },
          aspectRatio: 16 / 9,
        },
        async (decodedText) => {
          if (processingLockRef.current) return;
          processingLockRef.current = true;

          setScanStatus("detected");
          setLastBarcode(decodedText);

          // 1. Paytm / GPay instant tactile feedback (Double-pulse vibration + audio chime)
          playScanSuccessFeedback();

          let imageBlob: Blob = new Blob([], { type: "image/jpeg" });
          try {
            const videoElem = videoContainerRef.current?.querySelector("video") as HTMLVideoElement | null;
            if (videoElem && videoElem.videoWidth > 0) {
              const canvas = document.createElement("canvas");
              canvas.width = videoElem.videoWidth;
              canvas.height = videoElem.videoHeight;
              const ctx = canvas.getContext("2d");
              if (ctx) {
                ctx.drawImage(videoElem, 0, 0);
                imageBlob = await new Promise<Blob>((resolve) => {
                  canvas.toBlob((b) => resolve(b || new Blob([], { type: "image/jpeg" })), "image/jpeg", 0.9);
                });
              }
            }
          } catch {
            // Frame capture fallback
          }

          // 2. Pause 550ms so user experiences the green scan feedback, vibration, and chime
          await new Promise((resolve) => setTimeout(resolve, 550));

          try {
            await scanner.stop();
          } catch {
            // Ignore stop errors
          }
          setIsScanning(false);

          await runVerification(decodedText, imageBlob);
        },
        () => {
          // Frame without barcode
        }
      );

      setIsScanning(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setCameraError(msg);
      setScanStatus("error");
      setIsScanning(false);
    }
  }, [runVerification]);

  /** Stop the scanner and release camera. */
  const stopScanner = useCallback(async () => {
    if (scannerRef.current) {
      try {
        await scannerRef.current.stop();
      } catch {
        // Ignore
      }
      scannerRef.current = null;
    }
    setIsScanning(false);
    setScanStatus("idle");
    setLastBarcode(null);
  }, []);

  /** Reset for a new scan. */
  const resetScanner = useCallback(() => {
    setLastBarcode(null);
    setScanStatus("idle");
    setIsProcessing(false);
    setProcessingStage("");
    processingLockRef.current = false;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (scannerRef.current) {
        scannerRef.current.stop().catch(() => {});
      }
    };
  }, []);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "1.5rem",
        width: "100%",
        maxWidth: "800px",
        margin: "0 auto",
      }}
    >
      {/* ================= FIELD RETICLE VIEWPORT ================= */}
      <motion.div
        ref={videoContainerRef}
        style={{
          width: "100%",
          aspectRatio: "16/9",
          borderRadius: "12px",
          overflow: "hidden",
          position: "relative",
          background: "#0f172a",
          border: scanStatus === "detected" ? "3px solid #10b981" : "2px solid #cbd5e1",
          boxShadow: scanStatus === "detected" ? "0 0 35px rgba(16, 185, 129, 0.75)" : "var(--shadow-card)",
          transition: "all 0.25s ease",
        }}
        animate={{
          scale: scanStatus === "detected" ? 1.02 : 1,
        }}
      >
        {/* Reticle Corner Brackets */}
        <div className="hud-corner hud-corner-tl" style={{ borderColor: scanStatus === "detected" ? "#10b981" : "#38bdf8" }} />
        <div className="hud-corner hud-corner-tr" style={{ borderColor: scanStatus === "detected" ? "#10b981" : "#38bdf8" }} />
        <div className="hud-corner hud-corner-bl" style={{ borderColor: scanStatus === "detected" ? "#10b981" : "#38bdf8" }} />
        <div className="hud-corner hud-corner-br" style={{ borderColor: scanStatus === "detected" ? "#10b981" : "#38bdf8" }} />

        {/* Viewfinder Telemetry Bar */}
        <div
          style={{
            position: "absolute",
            top: 12,
            left: 16,
            right: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            zIndex: 15,
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              fontWeight: 600,
              color: "#ffffff",
              background: "rgba(15, 23, 42, 0.85)",
              padding: "0.25rem 0.65rem",
              borderRadius: "4px",
              border: "1px solid #334155",
            }}
          >
            <Radio size={12} color="#38bdf8" />
            <span>{t("camera_field")}</span>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              fontWeight: 600,
              color: isScanning ? "#86efac" : "#cbd5e1",
              background: "rgba(15, 23, 42, 0.85)",
              padding: "0.25rem 0.65rem",
              borderRadius: "4px",
              border: "1px solid #334155",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: isScanning ? "#22c55e" : "#94a3b8",
              }}
            />
            <span>{isScanning ? t("camera_live") : t("camera_ready")}</span>
          </div>
        </div>

        {/* html5-qrcode video element target */}
        <div
          id={SCANNER_ELEMENT_ID}
          style={{
            width: "100%",
            height: "100%",
            display: isScanning ? "block" : "none",
          }}
        />

        {/* Idle Reticle Display */}
        {!isScanning && !isProcessing && scanStatus === "idle" && (
          <div
            style={{
              width: "100%",
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "1rem",
              padding: "2rem",
              position: "relative",
              color: "#ffffff",
            }}
          >
            <div
              style={{
                width: "260px",
                height: "170px",
                border: "2px dashed #38bdf8",
                borderRadius: "8px",
                background: "rgba(56, 189, 248, 0.05)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "0.5rem",
              }}
            >
              <Crosshair size={32} color="#38bdf8" />
              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#e2e8f0" }}>
                {t("align_barcode_reticle")}
              </span>
            </div>

            <p style={{ color: "#94a3b8", fontSize: "0.8rem", maxWidth: "440px", textAlign: "center" }}>
              {t("camera_support_desc")}
            </p>
          </div>
        )}

        {/* Paytm-Style Instant Barcode Captured Affirmation Overlay */}
        <AnimatePresence>
          {scanStatus === "detected" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              style={{
                position: "absolute",
                inset: 0,
                background: "rgba(6, 78, 59, 0.88)",
                backdropFilter: "blur(6px)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "0.85rem",
                zIndex: 40,
                color: "#ffffff",
              }}
            >
              <motion.div
                initial={{ scale: 0, rotate: -20 }}
                animate={{ scale: [0, 1.25, 1], rotate: 0 }}
                transition={{ duration: 0.32, ease: "easeOut" }}
                style={{
                  width: "72px",
                  height: "72px",
                  borderRadius: "50%",
                  background: "#10b981",
                  boxShadow: "0 0 35px rgba(16, 185, 129, 0.9)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <CheckCircle2 size={44} color="#ffffff" />
              </motion.div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: "1.15rem", fontWeight: 800, letterSpacing: "0.03em" }}>
                  {lang === "hi" ? "बारकोड सफलतापूर्वक कैप्चर!" : "BARCODE CAPTURED!"}
                </div>
                <div
                  style={{
                    fontSize: "0.9rem",
                    fontFamily: "var(--font-mono)",
                    color: "#a7f3d0",
                    fontWeight: 700,
                    marginTop: "3px",
                  }}
                >
                  {lastBarcode}
                </div>
                <div style={{ fontSize: "0.78rem", color: "#d1fae5", marginTop: "4px" }}>
                  {lang === "hi" ? "वैधानिक अनुपालन विश्लेषण प्रारंभ..." : "Proceeding to Statutory Verification..."}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Processing State Overlay */}
        <AnimatePresence>
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{
                position: "absolute",
                inset: 0,
                background: "rgba(15, 23, 42, 0.92)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "1rem",
                zIndex: 20,
                color: "#ffffff",
              }}
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
              >
                <Loader2 size={40} color="#38bdf8" />
              </motion.div>
              <div style={{ textAlign: "center" }}>
                <p style={{ color: "#38bdf8", fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.25rem" }}>
                  {processingStage || "Evaluating Commodity Statutory Compliance..."}
                </p>
                <p style={{ color: "#94a3b8", fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                  LEGAL METROLOGY ACT, 2009 • RULE 6 VERIFICATION
                </p>
              </div>

              {lastBarcode && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "0.4rem 0.85rem",
                    borderRadius: "6px",
                    background: "rgba(56, 189, 248, 0.15)",
                    border: "1px solid rgba(56, 189, 248, 0.3)",
                  }}
                >
                  <Barcode size={16} color="#38bdf8" />
                  <span style={{ color: "#ffffff", fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 600 }}>
                    {lastBarcode}
                  </span>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Camera Error Message */}
        {cameraError && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.75rem",
              padding: "2rem",
              background: "rgba(15, 23, 42, 0.95)",
              color: "#ffffff",
            }}
          >
            <CameraOff size={40} color="#ef4444" />
            <div style={{ textAlign: "center" }}>
              <p style={{ color: "#fca5a5", fontSize: "0.9rem", fontWeight: 700, marginBottom: "0.25rem" }}>
                Camera Access Unavailable
              </p>
              <p style={{ color: "#94a3b8", fontSize: "0.78rem", maxWidth: "380px" }}>
                {cameraError.includes("Permission")
                  ? "Please permit camera access in your browser, or test with the Reference Market Samples below."
                  : cameraError}
              </p>
            </div>
          </div>
        )}
      </motion.div>

      {/* ================= PRIMARY ACTION CONTROLS ================= */}
      <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}>
        {!isScanning && !isProcessing && (
          <button
            onClick={async () => {
              resetScanner();
              await startScanner();
            }}
            className="btn-gov-primary"
            style={{ padding: "0.75rem 1.75rem", fontSize: "0.92rem" }}
          >
            <Camera size={18} />
            <span>{scanStatus === "idle" ? t("activate_camera") : t("scan_another")}</span>
          </button>
        )}

        {isScanning && (
          <button
            onClick={stopScanner}
            className="btn-gov-danger"
            style={{ padding: "0.75rem 1.75rem", fontSize: "0.92rem" }}
          >
            <CameraOff size={18} />
            <span>{t("deactivate_camera")}</span>
          </button>
        )}
      </div>

      {/* ================= MANUAL BARCODE / FSSAI SEARCH ================= */}
      <div className="gov-card" style={{ width: "100%", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.65rem" }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--gov-navy-dark)" }}>
            {t("manual_search_title")}
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {t("manual_search_sub")}
          </span>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (manualInput.trim()) {
              setLastBarcode(manualInput.trim());
              setScanStatus("detected");
              playScanSuccessFeedback();
              setTimeout(() => {
                runVerification(manualInput.trim());
              }, 500);
            }
          }}
          style={{ display: "flex", gap: "0.65rem" }}
        >
          <input
            type="text"
            value={manualInput}
            onChange={(e) => setManualInput(e.target.value)}
            placeholder={t("manual_placeholder")}
            style={{
              flex: 1,
              padding: "0.65rem 0.85rem",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-card)",
              fontSize: "0.88rem",
              fontFamily: "var(--font-mono)",
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={isProcessing || !manualInput.trim()}
            className="btn-gov-primary"
          >
            <Search size={15} />
            <span>{t("verify_button")}</span>
          </button>
        </form>
      </div>

      {/* ================= REFERENCE MARKET TEST SAMPLES ================= */}
      <div style={{ width: "100%" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--gov-navy-dark)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            📋 Reference Market Test Samples (Instant Simulation)
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Select sample to simulate officer audit</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "0.75rem" }}>
          {DEMO_PRODUCTS.map((prod) => (
            <button
              key={prod.barcode}
              onClick={() => {
                setLastBarcode(prod.barcode);
                setScanStatus("detected");
                playScanSuccessFeedback();
                setTimeout(() => {
                  runVerification(prod.barcode);
                }, 500);
              }}
              disabled={isProcessing}
              className="gov-card"
              style={{
                padding: "0.85rem 1rem",
                display: "flex",
                alignItems: "flex-start",
                gap: "0.75rem",
                textAlign: "left",
                cursor: "pointer",
                background: "#ffffff",
                transition: "all 0.15s ease",
              }}
            >
              <span style={{ fontSize: "1.5rem" }}>{prod.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.2rem" }}>
                  <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--gov-navy-dark)" }}>
                    {prod.name}
                  </span>
                  <span
                    style={{
                      fontSize: "0.68rem",
                      fontWeight: 700,
                      color: prod.color,
                      background: `${prod.color}15`,
                      padding: "0.15rem 0.45rem",
                      borderRadius: "4px",
                      border: `1px solid ${prod.color}35`,
                    }}
                  >
                    {prod.badge}
                  </span>
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.25rem" }}>
                  {prod.desc}
                </p>
                <div style={{ fontSize: "0.72rem", color: "var(--gov-navy-primary)", fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                  Barcode: {prod.barcode}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ================= 3 STATUTORY STATUS CATEGORIES ================= */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", width: "100%" }}>
        {[
          {
            icon: <ShieldCheck size={18} color="#15803d" />,
            label: "STATUTORY COMPLIANT",
            color: "#15803d",
            bg: "#f0fdf4",
            border: "#bbf7d0",
            desc: "Rule 6 mandatory declarations verified • Valid FSSAI • Authentic barcode",
          },
          {
            icon: <ShieldAlert size={18} color="#d97706" />,
            label: "FURTHER REVIEW REQUIRED",
            color: "#d97706",
            bg: "#fffbeb",
            border: "#fde68a",
            desc: "Dual pricing discrepancy • Importer details review • Near expiry (<30d)",
          },
          {
            icon: <ShieldX size={18} color="#b91c1c" />,
            label: "ACTIONABLE NON-COMPLIANCE",
            color: "#b91c1c",
            bg: "#fef2f2",
            border: "#fecaca",
            desc: "Missing mandatory disclosures • Notice under Section 36 actionable",
          },
        ].map((item) => (
          <div
            key={item.label}
            style={{
              padding: "0.85rem",
              borderRadius: "var(--radius-md)",
              background: item.bg,
              border: `1px solid ${item.border}`,
              textAlign: "center",
            }}
          >
            <div style={{ marginBottom: "0.25rem" }}>{item.icon}</div>
            <div style={{ color: item.color, fontSize: "0.75rem", fontWeight: 700 }}>
              {item.label}
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: "0.7rem", marginTop: "0.2rem" }}>
              {item.desc}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
