/**
 * SIH26034 — Live Camera Barcode Scanner & Statutory Verification Cockpit
 * Department of Consumer Affairs • Government of India
 *
 * Real-time package scanning using the device camera with
 * html5-qrcode for barcode/QR detection, interactive reference
 * demo products, manual barcode lookup, instant frame capture,
 * and direct file image scanning.
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
  Upload,
  SwitchCamera,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { Html5Qrcode, Html5QrcodeSupportedFormats } from "html5-qrcode";
import { scanPackage, auditImage } from "../api";
import type { AuditResponse } from "../api";
import { useLanguage } from "../context/LanguageContext";
import { playScanSuccessFeedback } from "../utils/hapticsAndSound";

interface LiveScannerProps {
  onScanComplete: (result: AuditResponse) => void;
  onError: (error: string) => void;
}

interface CameraDevice {
  id: string;
  label: string;
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
  const [scanStatus, setScanStatus] = useState<
    "idle" | "scanning" | "detected" | "processing" | "success" | "error"
  >("idle");
  const [processingStage, setProcessingStage] = useState("");
  const [cameraError, setCameraError] = useState<string | null>(null);

  // Multiple camera selection state
  const [availableCameras, setAvailableCameras] = useState<CameraDevice[]>([]);
  const [currentCameraId, setCurrentCameraId] = useState<string | null>(null);

  const scannerRef = useRef<Html5Qrcode | null>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const processingLockRef = useRef(false);

  const SCANNER_ELEMENT_ID = "lmpc-barcode-scanner";

  /** Run complete verification on a given barcode string. */
  const runVerification = useCallback(
    async (barcode: string, imageBlob?: Blob) => {
      try {
        setIsProcessing(true);
        setScanStatus("processing");
        setLastBarcode(barcode);
        setProcessingStage(lang === "hi" ? "मल्टी-एजेंट वैधानिक पाइपलाइन से जुड़ाव..." : "Connecting to Multi-Agent Statutory Pipeline...");
        await new Promise((r) => setTimeout(r, 350));

        setProcessingStage(lang === "hi" ? "GS1 इंडिया डेटाकार्ट और ओपन फूड फैक्ट्स खोज..." : "Querying GS1 India DataKart & Open Food Facts...");
        await new Promise((r) => setTimeout(r, 350));

        setProcessingStage(lang === "hi" ? "FSSAI 14-अंकीय फोस्कोस लाइसेंस सत्यापन..." : "Validating FSSAI 14-Digit FoSCoS License...");
        await new Promise((r) => setTimeout(r, 300));

        setProcessingStage(lang === "hi" ? "विधिक मापविज्ञान अधिनियम, 2009 नियम 6 मूल्यांकन..." : "Evaluating Legal Metrology Act, 2009 Rule 6 Declarations...");

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
    [lang, onScanComplete, onError]
  );

  /** Stop scanner safely. */
  const stopScanner = useCallback(async () => {
    if (scannerRef.current) {
      try {
        if (scannerRef.current.isScanning) {
          await scannerRef.current.stop();
        }
      } catch {
        // Ignore stop errors
      }
      scannerRef.current = null;
    }
    setIsScanning(false);
    setScanStatus("idle");
  }, []);

  /** Handle decoded barcode callback. */
  const handleBarcodeDecoded = useCallback(
    async (decodedText: string) => {
      if (processingLockRef.current) return;
      processingLockRef.current = true;

      setScanStatus("detected");
      setLastBarcode(decodedText);

      // Instant Paytm / GPay style affirmative haptic vibration & melodic sound
      playScanSuccessFeedback();

      // Capture frame from active video element
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

      // Visual pause so officer experiences affirmative green flash and vibration
      await new Promise((resolve) => setTimeout(resolve, 550));

      // Stop camera before processing heavy verification
      try {
        if (scannerRef.current && scannerRef.current.isScanning) {
          await scannerRef.current.stop();
        }
      } catch {
        // Ignore
      }
      setIsScanning(false);

      await runVerification(decodedText, imageBlob);
    },
    [runVerification]
  );

  /** Initialize camera and start scanning. */
  const startScanner = useCallback(
    async (targetCameraId?: string) => {
      setCameraError(null);
      setScanStatus("scanning");
      setIsScanning(true);
      processingLockRef.current = false;

      // Small tick to ensure container element is mounted and sized
      await new Promise((resolve) => setTimeout(resolve, 60));

      try {
        if (scannerRef.current) {
          try {
            if (scannerRef.current.isScanning) {
              await scannerRef.current.stop();
            }
          } catch {
            // Ignore
          }
          scannerRef.current = null;
        }

        // 1. Enumerate cameras
        let cameras: CameraDevice[] = [];
        try {
          const devices = await Html5Qrcode.getCameras();
          if (devices && devices.length > 0) {
            cameras = devices.map((d) => ({ id: d.id, label: d.label || `Camera ${d.id.slice(0, 5)}` }));
            setAvailableCameras(cameras);
          }
        } catch {
          // Camera enumeration not supported or permission pending
        }

        // 2. Select camera ID or facing mode
        let cameraToUse: string | { facingMode: string } = { facingMode: "environment" };
        if (targetCameraId) {
          cameraToUse = targetCameraId;
          setCurrentCameraId(targetCameraId);
        } else if (cameras.length > 0) {
          const rearCam = cameras.find((c) => /back|rear|environment/i.test(c.label));
          const selected = rearCam || cameras[0];
          cameraToUse = selected.id;
          setCurrentCameraId(selected.id);
        }

        // 3. Create scanner instance with high-speed barcode format support & native engine
        const scanner = new Html5Qrcode(SCANNER_ELEMENT_ID, {
          formatsToSupport: [
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.CODE_39,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
            Html5QrcodeSupportedFormats.QR_CODE,
            Html5QrcodeSupportedFormats.DATA_MATRIX,
          ],
          experimentalFeatures: {
            useBarCodeDetectorIfSupported: true,
          },
          verbose: false,
        });
        scannerRef.current = scanner;

        // Dynamic responsive qrbox size
        const scanConfig = {
          fps: 20,
          qrbox: (viewfinderWidth: number, viewfinderHeight: number) => {
            const width = Math.floor(Math.min(viewfinderWidth * 0.85, 480));
            const height = Math.floor(Math.min(viewfinderHeight * 0.70, 260));
            return {
              width: Math.max(width, 220),
              height: Math.max(height, 140),
            };
          },
          aspectRatio: 16 / 9,
        };

        try {
          await scanner.start(
            cameraToUse,
            scanConfig,
            handleBarcodeDecoded,
            () => {} // Frame with no barcode
          );
        } catch (firstStartErr) {
          console.warn("Primary camera start failed, trying generic fallback:", firstStartErr);
          // Fallback to user facing mode or basic camera
          await scanner.start(
            { facingMode: "user" },
            scanConfig,
            handleBarcodeDecoded,
            () => {}
          );
        }

        setIsScanning(true);
      } catch (err: unknown) {
        console.error("Camera activation error:", err);
        const rawMsg = err instanceof Error ? err.message : String(err);
        let userFriendlyMsg = rawMsg;

        if (rawMsg.includes("NotAllowedError") || rawMsg.includes("Permission")) {
          userFriendlyMsg = "Camera permission was denied. Please allow camera access in your browser settings.";
        } else if (rawMsg.includes("NotFoundError") || rawMsg.includes("DevicesNotFoundError")) {
          userFriendlyMsg = "No camera found on this device. You can use 'Upload Packaging Photo' or test with the Reference Market Samples below.";
        } else if (typeof window !== "undefined" && !window.isSecureContext && location.hostname !== "localhost") {
          userFriendlyMsg = "Camera access requires HTTPS or localhost. If opening remotely, use HTTPS or upload a photo.";
        }

        setCameraError(userFriendlyMsg);
        setScanStatus("error");
        setIsScanning(false);
      }
    },
    [handleBarcodeDecoded]
  );

  /** Switch between front/back or external cameras. */
  const switchCamera = useCallback(async () => {
    if (availableCameras.length <= 1) return;
    const currentIndex = availableCameras.findIndex((c) => c.id === currentCameraId);
    const nextIndex = (currentIndex + 1) % availableCameras.length;
    const nextCamera = availableCameras[nextIndex];
    if (nextCamera) {
      await stopScanner();
      await startScanner(nextCamera.id);
    }
  }, [availableCameras, currentCameraId, stopScanner, startScanner]);

  /** Capture current camera frame and perform full multimodal LMPC compliance audit. */
  const handleCaptureFrameAndAudit = useCallback(async () => {
    if (processingLockRef.current) return;
    processingLockRef.current = true;

    playScanSuccessFeedback();

    let capturedBlob: Blob | null = null;
    try {
      const videoElem = videoContainerRef.current?.querySelector("video") as HTMLVideoElement | null;
      if (videoElem && videoElem.videoWidth > 0) {
        const canvas = document.createElement("canvas");
        canvas.width = videoElem.videoWidth;
        canvas.height = videoElem.videoHeight;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.drawImage(videoElem, 0, 0);
          capturedBlob = await new Promise<Blob | null>((resolve) => {
            canvas.toBlob((b) => resolve(b), "image/jpeg", 0.95);
          });
        }
      }
    } catch {
      // Capture error
    }

    try {
      if (scannerRef.current && scannerRef.current.isScanning) {
        await scannerRef.current.stop();
      }
    } catch {
      // Ignore
    }
    setIsScanning(false);

    if (capturedBlob) {
      const file = new File([capturedBlob], "inspection-capture.jpg", { type: "image/jpeg" });
      setIsProcessing(true);
      setScanStatus("processing");
      setProcessingStage(lang === "hi" ? "कैप्चर किए गए लेबल पर जेमिनी मल्टीमॉडल ओसीआर विश्लेषण..." : "Running Gemini Multimodal OCR on captured label...");
      try {
        const auditResult = await auditImage(file);
        setScanStatus("success");
        onScanComplete(auditResult);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setScanStatus("error");
        onError(msg || "Failed to audit captured frame.");
      } finally {
        setIsProcessing(false);
        processingLockRef.current = false;
      }
    } else {
      processingLockRef.current = false;
    }
  }, [lang, onScanComplete, onError]);

  /** Handle file upload scan for barcodes and packaging photos. */
  const handleFileScan = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      setIsProcessing(true);
      setScanStatus("processing");
      setProcessingStage(lang === "hi" ? "छवि में बारकोड एवं वैधानिक लेबल की खोज..." : "Scanning image for barcodes & statutory labels...");

      try {
        let decodedBarcode: string | null = null;
        try {
          const tempScanner = scannerRef.current || new Html5Qrcode(SCANNER_ELEMENT_ID);
          decodedBarcode = await tempScanner.scanFile(file, false);
        } catch {
          // No barcode found in file, continue to multimodal audit
        }

        playScanSuccessFeedback();

        if (decodedBarcode) {
          setLastBarcode(decodedBarcode);
          await runVerification(decodedBarcode, file);
        } else {
          // Direct multimodal vision audit
          setProcessingStage(lang === "hi" ? "विधिक मापविज्ञान नियम 6 अनिवार्य घोषणाओं की जांच..." : "Evaluating Legal Metrology Act Rule 6 declarations...");
          const auditResult = await auditImage(file);
          setScanStatus("success");
          onScanComplete(auditResult);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setScanStatus("error");
        onError(msg || "Failed to analyze image file.");
      } finally {
        setIsProcessing(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [lang, runVerification, onScanComplete, onError]
  );

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
        try {
          if (scannerRef.current.isScanning) {
            scannerRef.current.stop().catch(() => {});
          }
        } catch {
          // Ignore
        }
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
      {/* Hidden File Input for Image Barcode / Label Scan */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: "none" }}
        onChange={handleFileScan}
      />

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
          border: scanStatus === "detected" ? "3px solid #10b981" : "2px solid #334155",
          boxShadow:
            scanStatus === "detected"
              ? "0 0 35px rgba(16, 185, 129, 0.75)"
              : isScanning
              ? "0 0 25px rgba(56, 189, 248, 0.35)"
              : "var(--shadow-card)",
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

        {/* Laser Sweep Line when Scanning */}
        {isScanning && !isProcessing && scanStatus !== "detected" && (
          <div className="scan-laser-line" />
        )}

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

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", pointerEvents: "auto" }}>
            {availableCameras.length > 1 && isScanning && (
              <button
                onClick={switchCamera}
                title={t("switch_camera")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  background: "rgba(15, 23, 42, 0.85)",
                  color: "#38bdf8",
                  border: "1px solid #334155",
                  padding: "0.25rem 0.55rem",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                }}
              >
                <SwitchCamera size={13} />
                <span>{t("switch_camera")}</span>
              </button>
            )}

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
                  boxShadow: isScanning ? "0 0 8px #22c55e" : "none",
                }}
              />
              <span>{isScanning ? t("camera_live") : t("camera_ready")}</span>
            </div>
          </div>
        </div>

        {/* html5-qrcode video element container (always present with positive dimensions to avoid qrbox crash) */}
        <div
          id={SCANNER_ELEMENT_ID}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            opacity: isScanning ? 1 : 0,
            pointerEvents: isScanning ? "auto" : "none",
            zIndex: 5,
          }}
        />

        {/* Idle Reticle Display */}
        {!isScanning && !isProcessing && scanStatus === "idle" && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "1rem",
              padding: "2rem",
              color: "#ffffff",
              zIndex: 8,
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
              <Crosshair size={34} color="#38bdf8" />
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
                backdropFilter: "blur(4px)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "1rem",
                zIndex: 35,
                color: "#ffffff",
              }}
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
              >
                <Loader2 size={42} color="#38bdf8" />
              </motion.div>
              <div style={{ textAlign: "center", padding: "0 1.5rem" }}>
                <p style={{ color: "#38bdf8", fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.25rem" }}>
                  {processingStage || t("evaluating_commodity")}
                </p>
                <p style={{ color: "#94a3b8", fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                  LEGAL METROLOGY ACT, 2009 • RULE 6 MULTI-AGENT VERIFICATION
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
              gap: "1rem",
              padding: "2rem",
              background: "rgba(15, 23, 42, 0.96)",
              color: "#ffffff",
              zIndex: 30,
            }}
          >
            <CameraOff size={42} color="#ef4444" />
            <div style={{ textAlign: "center" }}>
              <p style={{ color: "#fca5a5", fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.35rem" }}>
                {lang === "hi" ? "कैमरा अनुपलब्ध" : "Camera Access Unavailable"}
              </p>
              <p style={{ color: "#94a3b8", fontSize: "0.8rem", maxWidth: "420px", lineHeight: "1.4" }}>
                {cameraError}
              </p>
            </div>

            <div style={{ display: "flex", gap: "0.65rem", flexWrap: "wrap", justifyContent: "center" }}>
              <button
                onClick={() => startScanner()}
                className="btn-gov-primary"
                style={{ padding: "0.5rem 1.2rem", fontSize: "0.82rem" }}
              >
                <RefreshCw size={14} />
                <span>{lang === "hi" ? "पुनः प्रयास करें" : "Retry Camera"}</span>
              </button>

              <button
                onClick={() => fileInputRef.current?.click()}
                className="btn-gov-secondary"
                style={{
                  padding: "0.5rem 1.2rem",
                  fontSize: "0.82rem",
                  background: "rgba(56, 189, 248, 0.15)",
                  color: "#38bdf8",
                  borderColor: "rgba(56, 189, 248, 0.4)",
                }}
              >
                <Upload size={14} />
                <span>{t("upload_scan_image")}</span>
              </button>
            </div>
          </div>
        )}
      </motion.div>

      {/* ================= PRIMARY ACTION CONTROLS ================= */}
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", justifyContent: "center" }}>
        {!isScanning && !isProcessing && (
          <>
            <button
              onClick={() => {
                resetScanner();
                startScanner();
              }}
              className="btn-gov-primary"
              style={{ padding: "0.75rem 1.75rem", fontSize: "0.92rem" }}
            >
              <Camera size={18} />
              <span>{scanStatus === "idle" ? t("activate_camera") : t("scan_another")}</span>
            </button>

            <button
              onClick={() => fileInputRef.current?.click()}
              className="btn-gov-secondary"
              style={{
                padding: "0.75rem 1.35rem",
                fontSize: "0.92rem",
                background: "#ffffff",
                border: "1px solid var(--border-card)",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                cursor: "pointer",
              }}
              title="Upload an image containing a barcode or package label"
            >
              <Upload size={17} color="var(--gov-navy-primary)" />
              <span>{t("upload_scan_image")}</span>
            </button>
          </>
        )}

        {isScanning && (
          <>
            {/* Direct Snapshot Capture & Multimodal Audit Button */}
            <button
              onClick={handleCaptureFrameAndAudit}
              disabled={isProcessing}
              className="btn-gov-primary"
              style={{
                padding: "0.75rem 1.75rem",
                fontSize: "0.92rem",
                background: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
                boxShadow: "0 0 20px rgba(2, 132, 199, 0.4)",
              }}
            >
              <Sparkles size={18} />
              <span>{t("capture_frame_btn")}</span>
            </button>

            <button
              onClick={stopScanner}
              className="btn-gov-danger"
              style={{ padding: "0.75rem 1.5rem", fontSize: "0.92rem" }}
            >
              <CameraOff size={18} />
              <span>{t("deactivate_camera")}</span>
            </button>
          </>
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
            📋 {lang === "hi" ? "संदर्भ बाजार परीक्षण नमूने (त्वरित सिमुलेशन)" : "Reference Market Test Samples (Instant Simulation)"}
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            {lang === "hi" ? "अधिकारी ऑडिट का अनुकरण करने के लिए नमूना चुनें" : "Select sample to simulate officer audit"}
          </span>
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
            label: lang === "hi" ? "वैधानिक अनुपालक" : "STATUTORY COMPLIANT",
            color: "#15803d",
            bg: "#f0fdf4",
            border: "#bbf7d0",
            desc: lang === "hi" ? "नियम 6 घोषणाएं सत्यापित • वैध FSSAI" : "Rule 6 mandatory declarations verified • Valid FSSAI",
          },
          {
            icon: <ShieldAlert size={18} color="#d97706" />,
            label: lang === "hi" ? "पुनरावलोकन आवश्यक" : "FURTHER REVIEW REQUIRED",
            color: "#d97706",
            bg: "#fffbeb",
            border: "#fde68a",
            desc: lang === "hi" ? "आयात विवरण समीक्षा • आसन्न समाप्ति" : "Dual pricing discrepancy • Near expiry (<30d)",
          },
          {
            icon: <ShieldX size={18} color="#b91c1c" />,
            label: lang === "hi" ? "कार्रवाई योग्य उल्लंघन" : "ACTIONABLE NON-COMPLIANCE",
            color: "#b91c1c",
            bg: "#fef2f2",
            border: "#fecaca",
            desc: lang === "hi" ? "गुम अनिवार्य प्रकटीकरण • धारा 36 नोटिस" : "Missing mandatory disclosures • Notice under Section 36 actionable",
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
