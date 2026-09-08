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
  Zap,
  ZapOff,
  Layers,
  Check,
  Trash2,
} from "lucide-react";
import { Html5Qrcode, Html5QrcodeSupportedFormats } from "html5-qrcode";
import { scanPackage, auditImage, auditMultiShot } from "../api";
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
  const [hasTorch, setHasTorch] = useState(false);
  const [isTorchOn, setIsTorchOn] = useState(false);

  // Multi-Shot Guided Capture state
  const [isMultiShotMode, setIsMultiShotMode] = useState(false);
  const [multiShots, setMultiShots] = useState<{
    front: File | null;
    back: File | null;
    barcode: File | null;
  }>({ front: null, back: null, barcode: null });
  const [multiShotPreviews, setMultiShotPreviews] = useState<{
    front: string | null;
    back: string | null;
    barcode: string | null;
  }>({ front: null, back: null, barcode: null });
  const [activeSlotFlash, setActiveSlotFlash] = useState<string | null>(null);

  const scannerRef = useRef<Html5Qrcode | null>(null);
  const nativeDetectorRef = useRef<any>(null);
  const nativeScanTimerRef = useRef<number | null>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const slotInputRefFront = useRef<HTMLInputElement>(null);
  const slotInputRefBack = useRef<HTMLInputElement>(null);
  const slotInputRefBarcode = useRef<HTMLInputElement>(null);
  const processingLockRef = useRef(false);

  const handleSlotFileUpload = useCallback((slot: "front" | "back" | "barcode", file: File) => {
    const previewUrl = URL.createObjectURL(file);
    setMultiShots((prev) => ({ ...prev, [slot]: file }));
    setMultiShotPreviews((prev) => {
      if (prev[slot]) URL.revokeObjectURL(prev[slot]!);
      return { ...prev, [slot]: previewUrl };
    });
  }, []);

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

  /** Toggle torch / flashlight if supported by active camera. */
  const toggleTorch = useCallback(async () => {
    try {
      const videoElem = videoContainerRef.current?.querySelector("video") as HTMLVideoElement | null;
      if (videoElem && videoElem.srcObject) {
        const stream = videoElem.srcObject as MediaStream;
        const track = stream.getVideoTracks()[0];
        if (track) {
          const nextState = !isTorchOn;
          await (track as any).applyConstraints({
            advanced: [{ torch: nextState }],
          });
          setIsTorchOn(nextState);
        }
      }
    } catch (err) {
      console.warn("Could not toggle camera torch:", err);
    }
  }, [isTorchOn]);

  /** Stop scanner safely. */
  const stopScanner = useCallback(async () => {
    if (nativeScanTimerRef.current) {
      clearTimeout(nativeScanTimerRef.current);
      nativeScanTimerRef.current = null;
    }
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
    setIsTorchOn(false);
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
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Stop camera before processing heavy verification
      try {
        if (nativeScanTimerRef.current) {
          clearTimeout(nativeScanTimerRef.current);
          nativeScanTimerRef.current = null;
        }
        if (scannerRef.current && scannerRef.current.isScanning) {
          await scannerRef.current.stop();
        }
      } catch {
        // Ignore
      }
      setIsTorchOn(false);
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

        // 1. Direct camera start without double getUserMedia call
        const cameraToUse = targetCameraId || { facingMode: "environment" };
        setCurrentCameraId(targetCameraId || null);

        // 2. Create scanner instance with high-speed 1D barcode format support & native engine
        const scanner = new Html5Qrcode(SCANNER_ELEMENT_ID, {
          formatsToSupport: [
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.CODE_39,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
            Html5QrcodeSupportedFormats.ITF,
            Html5QrcodeSupportedFormats.CODABAR,
            Html5QrcodeSupportedFormats.QR_CODE,
            Html5QrcodeSupportedFormats.DATA_MATRIX,
          ],
          experimentalFeatures: {
            useBarCodeDetectorIfSupported: true,
          },
          verbose: false,
        });
        scannerRef.current = scanner;

        // Generous viewport accommodating 1D barcodes horizontally, tilted, and 2D QR codes
        const scanConfig = {
          fps: 15,
          aspectRatio: 16 / 9,
          qrbox: (viewfinderWidth: number, viewfinderHeight: number) => {
            const w = Math.min(Math.floor(viewfinderWidth * 0.92), 560);
            const h = Math.min(Math.floor(viewfinderHeight * 0.65), 320);
            return { width: Math.max(w, 240), height: Math.max(h, 150) };
          },
          videoConstraints: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280, min: 640 },
            height: { ideal: 720, min: 480 },
          },
        };

        try {
          await scanner.start(
            cameraToUse,
            scanConfig,
            handleBarcodeDecoded,
            () => {} // Frame with no barcode
          );
        } catch (firstStartErr) {
          console.warn("Primary camera start failed, trying user-facing webcam fallback:", firstStartErr);
          // Fallback to user-facing mode or default webcam
          await scanner.start(
            { facingMode: "user" },
            scanConfig,
            handleBarcodeDecoded,
            () => {}
          );
        }

        setIsScanning(true);

        // 3. Hardware-accelerated native BarcodeDetector loop (parallel boost)
        if (typeof window !== "undefined" && "BarcodeDetector" in window) {
          try {
            nativeDetectorRef.current = new (window as any).BarcodeDetector({
              formats: [
                "ean_13",
                "ean_8",
                "upc_a",
                "upc_e",
                "code_128",
                "code_39",
                "qr_code",
                "data_matrix",
              ],
            });

            const checkNativeBarcode = async () => {
              if (processingLockRef.current || !scannerRef.current) return;
              const videoElem = videoContainerRef.current?.querySelector("video") as HTMLVideoElement | null;
              if (videoElem && videoElem.readyState >= 2 && videoElem.videoWidth > 0) {
                try {
                  const detected = await nativeDetectorRef.current.detect(videoElem);
                  if (detected && detected.length > 0 && detected[0].rawValue) {
                    const code = String(detected[0].rawValue).trim();
                    if (code && !processingLockRef.current) {
                      handleBarcodeDecoded(code);
                      return;
                    }
                  }
                } catch {
                  // Ignore frame decode miss
                }
              }
              nativeScanTimerRef.current = window.setTimeout(checkNativeBarcode, 75);
            };

            nativeScanTimerRef.current = window.setTimeout(checkNativeBarcode, 350);
          } catch (e) {
            console.debug("Native BarcodeDetector loop skipped:", e);
          }
        }

        // 4. Check for torch / flashlight capability on active stream
        setTimeout(() => {
          try {
            const videoElem = videoContainerRef.current?.querySelector("video") as HTMLVideoElement | null;
            if (videoElem && videoElem.srcObject) {
              const stream = videoElem.srcObject as MediaStream;
              const track = stream.getVideoTracks()[0];
              if (track) {
                const caps: any = (track as any).getCapabilities?.() || {};
                if (caps.torch) {
                  setHasTorch(true);
                }
              }
            }
          } catch {
            // ignore capability check failure
          }
        }, 500);

        // 5. Enumerate devices in background without disrupting active video stream
        try {
          if (navigator.mediaDevices?.enumerateDevices) {
            const allDevs = await navigator.mediaDevices.enumerateDevices();
            const videoDevs = allDevs
              .filter((d) => d.kind === "videoinput")
              .map((d, idx) => ({ id: d.deviceId, label: d.label || `Camera ${idx + 1}` }));
            if (videoDevs.length > 0) {
              setAvailableCameras(videoDevs);
            }
          }
        } catch {
          // Ignore enumeration failure
        }
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
    let canvasElem: HTMLCanvasElement | null = null;
    try {
      const videoElem = videoContainerRef.current?.querySelector("video") as HTMLVideoElement | null;
      if (videoElem && videoElem.videoWidth > 0) {
        canvasElem = document.createElement("canvas");
        canvasElem.width = videoElem.videoWidth;
        canvasElem.height = videoElem.videoHeight;
        const ctx = canvasElem.getContext("2d");
        if (ctx) {
          ctx.drawImage(videoElem, 0, 0);
          capturedBlob = await new Promise<Blob | null>((resolve) => {
            canvasElem!.toBlob((b) => resolve(b), "image/jpeg", 0.95);
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

    if (capturedBlob && canvasElem) {
      const file = new File([capturedBlob], "inspection-capture.jpg", { type: "image/jpeg" });
      setIsProcessing(true);
      setScanStatus("processing");
      setProcessingStage(lang === "hi" ? "कैप्चर किए गए फ्रेम में बारकोड की उच्च-रिज़ॉल्यूशन खोज..." : "High-resolution barcode inspection on captured frame...");

      // 1. High-resolution barcode detection on captured frame
      let decodedBarcode: string | null = null;
      try {
        if (nativeDetectorRef.current) {
          const detected = await nativeDetectorRef.current.detect(canvasElem);
          if (detected && detected.length > 0 && detected[0].rawValue) {
            decodedBarcode = String(detected[0].rawValue).trim();
          }
        }
      } catch {
        // Native detection skip
      }

      if (!decodedBarcode && scannerRef.current) {
        try {
          decodedBarcode = await scannerRef.current.scanFile(file, false);
        } catch {
          // File scan miss
        }
      }

      // If a barcode was found in the captured frame, run tailored statutory verification!
      if (decodedBarcode) {
        setLastBarcode(decodedBarcode);
        await runVerification(decodedBarcode, capturedBlob);
        return;
      }

      // 2. Client-side Image Gate pre-check: test for hand / skin-tone / featureless frame
      let isHandOrNonPackaging = false;
      try {
        const ctx = canvasElem.getContext("2d");
        if (ctx) {
          const sampleW = Math.min(canvasElem.width, 160);
          const sampleH = Math.min(canvasElem.height, 160);
          const imgData = ctx.getImageData(0, 0, sampleW, sampleH);
          const data = imgData.data;
          let diffSum = 0;
          let skinPixels = 0;
          const totalPixels = sampleW * sampleH;

          for (let i = 0; i < data.length - 4; i += 4) {
            const r = data[i], g = data[i + 1], b = data[i + 2];
            const nextR = data[i + 4], nextG = data[i + 5], nextB = data[i + 6];
            diffSum += Math.abs(r - nextR) + Math.abs(g - nextG) + Math.abs(b - nextB);

            // Perceptual human skin tone filter (RGB color space)
            if (
              r > 95 &&
              g > 40 &&
              b > 20 &&
              Math.max(r, g, b) - Math.min(r, g, b) > 15 &&
              Math.abs(r - g) > 15 &&
              r > g &&
              r > b
            ) {
              skinPixels++;
            }
          }

          const avgVariation = diffSum / (totalPixels * 3);
          const skinFrac = skinPixels / totalPixels;

          // If frame is dominated by skin-tone with low edge variation, refuse immediately
          if (skinFrac > 0.50 && avgVariation < 14) {
            isHandOrNonPackaging = true;
          }
        }
      } catch {
        // Canvas analysis fallback
      }

      if (isHandOrNonPackaging) {
        setIsProcessing(false);
        processingLockRef.current = false;
        setScanStatus("error");
        onScanComplete({
          input_type: "camera",
          stage: "completed",
          status: "REFUSED",
          audit_status: "REFUSED",
          error: "No pre-packaged commodity barcode or statutory declarations detected.",
          reason: "The captured frame appears to show a human hand or person, not pre-packaged commodity packaging. Section 18(1) compliance audits require visible statutory declarations (MRP, Net Quantity, Manufacturer details) or an authentic barcode.",
          guidance: "Please hold the physical product package or barcode directly within the reticle under clear lighting.",
          image_assessment: {
            status: "CONTAINS_PERSON_OR_HAND",
            usable: false,
            reason: "High skin-fraction detected; no packaging declarations found.",
          },
          extractions: {},
          verdict: null,
        });
        return;
      }

      // 3. Frame has printed content or contrast: forward to statutory multimodal vision pipeline
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
  }, [lang, onScanComplete, onError, runVerification]);

  /** Capture the current live video frame into a multi-shot slot without stopping the camera */
  const captureCurrentFrameToSlot = useCallback(async (slot: "front" | "back" | "barcode") => {
    try {
      const videoElem = videoContainerRef.current?.querySelector("video") as HTMLVideoElement | null;
      if (!videoElem || videoElem.videoWidth === 0) return;

      const canvasElem = document.createElement("canvas");
      canvasElem.width = videoElem.videoWidth;
      canvasElem.height = videoElem.videoHeight;
      const ctx = canvasElem.getContext("2d");
      if (!ctx) return;

      ctx.drawImage(videoElem, 0, 0);
      const capturedBlob = await new Promise<Blob | null>((resolve) => {
        canvasElem.toBlob((b) => resolve(b), "image/jpeg", 0.95);
      });

      if (capturedBlob) {
        playScanSuccessFeedback();
        setActiveSlotFlash(slot);
        setTimeout(() => setActiveSlotFlash(null), 600);

        const fileName = `inspection_${slot}_panel.jpg`;
        const file = new File([capturedBlob], fileName, { type: "image/jpeg" });
        const previewUrl = URL.createObjectURL(capturedBlob);

        setMultiShots((prev) => ({ ...prev, [slot]: file }));
        setMultiShotPreviews((prev) => {
          if (prev[slot]) URL.revokeObjectURL(prev[slot]!);
          return { ...prev, [slot]: previewUrl };
        });
      }
    } catch (e) {
      console.error("Frame capture to slot error:", e);
    }
  }, []);

  /** Clear a captured slot */
  const clearSlot = useCallback((slot: "front" | "back" | "barcode") => {
    setMultiShots((prev) => ({ ...prev, [slot]: null }));
    setMultiShotPreviews((prev) => {
      if (prev[slot]) URL.revokeObjectURL(prev[slot]!);
      return { ...prev, [slot]: null };
    });
  }, []);

  /** Reset all multi-shot slots */
  const resetAllSlots = useCallback(() => {
    setMultiShotPreviews((prev) => {
      Object.values(prev).forEach((url) => {
        if (url) URL.revokeObjectURL(url);
      });
      return { front: null, back: null, barcode: null };
    });
    setMultiShots({ front: null, back: null, barcode: null });
  }, []);

  /** Execute multi-shot unified statutory audit */
  const handleExecuteMultiShotAudit = useCallback(async () => {
    const capturedCount = [multiShots.front, multiShots.back, multiShots.barcode].filter(Boolean).length;
    if (capturedCount === 0) {
      onError(lang === "hi" ? "कृपया कम से कम एक पैनल कैप्चर करें।" : "Please capture at least one packaging panel (Front PDP or Back Declarations).");
      return;
    }

    try {
      if (scannerRef.current && scannerRef.current.isScanning) {
        await scannerRef.current.stop();
      }
    } catch {
      // Ignore
    }
    setIsScanning(false);
    setIsProcessing(true);
    setScanStatus("processing");
    setProcessingStage(lang === "hi" ? "मल्टी-शॉट पैकेजिंग का एकीकृत वैधानिक विश्लेषण (LMPC नियम 6)..." : "Auditing unified multi-shot packaging panels under LMPC Rule 6...");

    try {
      const result = await auditMultiShot(multiShots);
      setScanStatus("success");
      onScanComplete(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setScanStatus("error");
      onError(msg || "Failed to audit multi-shot packaging.");
    } finally {
      setIsProcessing(false);
    }
  }, [multiShots, lang, onScanComplete, onError]);

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
          // Pass to scanPackage: backend checks image gate with OpenCV/ZXing for barcode first!
          setProcessingStage(lang === "hi" ? "छवि में बारकोड एवं वैधानिक घोषणाओं की खोज..." : "Analyzing packaging image for barcodes & mandatory declarations...");
          const auditResult = await scanPackage(file);
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
      if (nativeScanTimerRef.current) {
        clearTimeout(nativeScanTimerRef.current);
        nativeScanTimerRef.current = null;
      }
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

  const capturedSlotsCount = [multiShots.front, multiShots.back, multiShots.barcode].filter(Boolean).length;

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

      {/* Hidden File Inputs for Direct Multi-Shot Slot Uploads */}
      <input
        ref={slotInputRefFront}
        type="file"
        accept="image/*"
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleSlotFileUpload("front", f);
        }}
      />
      <input
        ref={slotInputRefBack}
        type="file"
        accept="image/*"
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleSlotFileUpload("back", f);
        }}
      />
      <input
        ref={slotInputRefBarcode}
        type="file"
        accept="image/*"
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleSlotFileUpload("barcode", f);
        }}
      />

      {/* ================= SCAN MODE TOGGLE PILL ================= */}
      <div
        style={{
          display: "flex",
          background: "var(--bg-secondary, #f1f5f9)",
          padding: "4px",
          borderRadius: "12px",
          gap: "6px",
          border: "1px solid var(--border-card, #e2e8f0)",
          width: "100%",
          maxWidth: "540px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
        }}
      >
        <button
          type="button"
          onClick={() => setIsMultiShotMode(false)}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
            padding: "8px 14px",
            borderRadius: "8px",
            border: "none",
            fontSize: "0.85rem",
            fontWeight: !isMultiShotMode ? 700 : 500,
            background: !isMultiShotMode ? "var(--gov-navy-primary, #002B49)" : "transparent",
            color: !isMultiShotMode ? "#ffffff" : "var(--text-muted, #64748b)",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
        >
          <Barcode size={16} />
          <span>{lang === "hi" ? "सिंगल स्कैन / बारकोड" : "Single Scan / Barcode"}</span>
        </button>

        <button
          type="button"
          onClick={() => setIsMultiShotMode(true)}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
            padding: "8px 14px",
            borderRadius: "8px",
            border: "none",
            fontSize: "0.85rem",
            fontWeight: isMultiShotMode ? 700 : 500,
            background: isMultiShotMode ? "var(--gov-navy-primary, #002B49)" : "transparent",
            color: isMultiShotMode ? "#ffffff" : "var(--text-muted, #64748b)",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
        >
          <Layers size={16} />
          <span>{lang === "hi" ? "मल्टी-शॉट पैकेजिंग (3 पैनल)" : "Multi-Shot Packaging (3 Panels)"}</span>
          {capturedSlotsCount > 0 && (
            <span
              style={{
                fontSize: "0.7rem",
                background: isMultiShotMode ? "#38bdf8" : "var(--gov-navy-primary, #002B49)",
                color: isMultiShotMode ? "#0f172a" : "#ffffff",
                padding: "1px 6px",
                borderRadius: "999px",
                fontWeight: 800,
              }}
            >
              {capturedSlotsCount}/3
            </span>
          )}
        </button>
      </div>

      {/* ================= MULTI-SHOT 3-PANEL GUIDED DOCK ================= */}
      {isMultiShotMode && (
        <div
          style={{
            width: "100%",
            background: "#ffffff",
            border: "1px solid var(--border-card, #e2e8f0)",
            borderRadius: "12px",
            padding: "1rem",
            boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Layers size={18} color="var(--gov-navy-primary, #002B49)" />
              <span style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--gov-navy-dark, #0f172a)" }}>
                {lang === "hi" ? "मल्टी-शॉट पैकेजिंग कैप्चर (एक वैधानिक पैकेज)" : "Multi-Shot Unified Packaging Capture (One Statutory Entity)"}
              </span>
            </div>
            <span style={{ fontSize: "0.74rem", fontFamily: "var(--font-mono)", color: "var(--text-muted, #64748b)" }}>
              {capturedSlotsCount}/3 {lang === "hi" ? "पैनल तैयार" : "Panels Staged"}
            </span>
          </div>

          {/* 3 Panels Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "0.75rem" }}>
            {/* Front Panel Slot */}
            <div
              style={{
                border: multiShots.front ? "2px solid #10b981" : activeSlotFlash === "front" ? "2px solid #38bdf8" : "1px dashed #cbd5e1",
                borderRadius: "8px",
                padding: "0.65rem",
                background: multiShots.front ? "rgba(16, 185, 129, 0.04)" : "#f8fafc",
                position: "relative",
                display: "flex",
                flexDirection: "column",
                gap: "0.4rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--gov-navy-dark, #0f172a)" }}>
                  {lang === "hi" ? "1. फ्रंट PDP" : "1. Front PDP"}
                </span>
                {multiShots.front ? (
                  <span style={{ fontSize: "0.68rem", color: "#059669", fontWeight: 700, display: "flex", alignItems: "center", gap: "2px" }}>
                    <Check size={12} /> {lang === "hi" ? "तैयार" : "Ready"}
                  </span>
                ) : (
                  <span style={{ fontSize: "0.68rem", color: "#94a3b8" }}>
                    {lang === "hi" ? "ब्रांड एवं MRP" : "Brand & MRP"}
                  </span>
                )}
              </div>

              {multiShotPreviews.front ? (
                <div style={{ position: "relative", height: "70px", borderRadius: "6px", overflow: "hidden" }}>
                  <img src={multiShotPreviews.front} alt="Front" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  <button
                    onClick={() => clearSlot("front")}
                    style={{
                      position: "absolute",
                      top: 4,
                      right: 4,
                      background: "rgba(0,0,0,0.6)",
                      border: "none",
                      color: "#fff",
                      borderRadius: "50%",
                      width: "20px",
                      height: "20px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      cursor: "pointer",
                    }}
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => slotInputRefFront.current?.click()}
                  style={{ height: "70px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "#f1f5f9", borderRadius: "6px", cursor: "pointer", border: "1px dashed #cbd5e1" }}
                  title="Click to upload file"
                >
                  <Upload size={14} color="#64748b" />
                  <span style={{ fontSize: "0.7rem", color: "#64748b", marginTop: "2px" }}>
                    {lang === "hi" ? "कैमरा या अपलोड" : "Snap or Upload"}
                  </span>
                </div>
              )}

              {isScanning && (
                <button
                  onClick={() => captureCurrentFrameToSlot("front")}
                  className="btn-gov-secondary"
                  style={{ fontSize: "0.75rem", padding: "0.35rem 0.6rem", width: "100%", justifyContent: "center" }}
                >
                  <Camera size={13} />
                  <span>{lang === "hi" ? "फ्रंट कैप्चर करें" : "Snap Front PDP"}</span>
                </button>
              )}
            </div>

            {/* Back Panel Slot */}
            <div
              style={{
                border: multiShots.back ? "2px solid #10b981" : activeSlotFlash === "back" ? "2px solid #38bdf8" : "1px dashed #cbd5e1",
                borderRadius: "8px",
                padding: "0.65rem",
                background: multiShots.back ? "rgba(16, 185, 129, 0.04)" : "#f8fafc",
                position: "relative",
                display: "flex",
                flexDirection: "column",
                gap: "0.4rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--gov-navy-dark, #0f172a)" }}>
                  {lang === "hi" ? "2. बैक घोषणाएं" : "2. Back Declarations"}
                </span>
                {multiShots.back ? (
                  <span style={{ fontSize: "0.68rem", color: "#059669", fontWeight: 700, display: "flex", alignItems: "center", gap: "2px" }}>
                    <Check size={12} /> {lang === "hi" ? "तैयार" : "Ready"}
                  </span>
                ) : (
                  <span style={{ fontSize: "0.68rem", color: "#94a3b8" }}>
                    {lang === "hi" ? "घोषणाएं व पता" : "Mfg, Date, Care"}
                  </span>
                )}
              </div>

              {multiShotPreviews.back ? (
                <div style={{ position: "relative", height: "70px", borderRadius: "6px", overflow: "hidden" }}>
                  <img src={multiShotPreviews.back} alt="Back" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  <button
                    onClick={() => clearSlot("back")}
                    style={{
                      position: "absolute",
                      top: 4,
                      right: 4,
                      background: "rgba(0,0,0,0.6)",
                      border: "none",
                      color: "#fff",
                      borderRadius: "50%",
                      width: "20px",
                      height: "20px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      cursor: "pointer",
                    }}
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => slotInputRefBack.current?.click()}
                  style={{ height: "70px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "#f1f5f9", borderRadius: "6px", cursor: "pointer", border: "1px dashed #cbd5e1" }}
                  title="Click to upload file"
                >
                  <Upload size={14} color="#64748b" />
                  <span style={{ fontSize: "0.7rem", color: "#64748b", marginTop: "2px" }}>
                    {lang === "hi" ? "कैमरा या अपलोड" : "Snap or Upload"}
                  </span>
                </div>
              )}

              {isScanning && (
                <button
                  onClick={() => captureCurrentFrameToSlot("back")}
                  className="btn-gov-secondary"
                  style={{ fontSize: "0.75rem", padding: "0.35rem 0.6rem", width: "100%", justifyContent: "center" }}
                >
                  <Camera size={13} />
                  <span>{lang === "hi" ? "बैक कैप्चर करें" : "Snap Back Panel"}</span>
                </button>
              )}
            </div>

            {/* Barcode / Sticker Slot */}
            <div
              style={{
                border: multiShots.barcode ? "2px solid #10b981" : activeSlotFlash === "barcode" ? "2px solid #38bdf8" : "1px dashed #cbd5e1",
                borderRadius: "8px",
                padding: "0.65rem",
                background: multiShots.barcode ? "rgba(16, 185, 129, 0.04)" : "#f8fafc",
                position: "relative",
                display: "flex",
                flexDirection: "column",
                gap: "0.4rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--gov-navy-dark, #0f172a)" }}>
                  {lang === "hi" ? "3. स्टिकर / बारकोड" : "3. Price Sticker / Barcode"}
                </span>
                {multiShots.barcode ? (
                  <span style={{ fontSize: "0.68rem", color: "#059669", fontWeight: 700, display: "flex", alignItems: "center", gap: "2px" }}>
                    <Check size={12} /> {lang === "hi" ? "तैयार" : "Ready"}
                  </span>
                ) : (
                  <span style={{ fontSize: "0.68rem", color: "#94a3b8" }}>
                    {lang === "hi" ? "वैकल्पिक" : "Optional"}
                  </span>
                )}
              </div>

              {multiShotPreviews.barcode ? (
                <div style={{ position: "relative", height: "70px", borderRadius: "6px", overflow: "hidden" }}>
                  <img src={multiShotPreviews.barcode} alt="Barcode / Sticker" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  <button
                    onClick={() => clearSlot("barcode")}
                    style={{
                      position: "absolute",
                      top: 4,
                      right: 4,
                      background: "rgba(0,0,0,0.6)",
                      border: "none",
                      color: "#fff",
                      borderRadius: "50%",
                      width: "20px",
                      height: "20px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      cursor: "pointer",
                    }}
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => slotInputRefBarcode.current?.click()}
                  style={{ height: "70px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "#f1f5f9", borderRadius: "6px", cursor: "pointer", border: "1px dashed #cbd5e1" }}
                  title="Click to upload file"
                >
                  <Upload size={14} color="#64748b" />
                  <span style={{ fontSize: "0.7rem", color: "#64748b", marginTop: "2px" }}>
                    {lang === "hi" ? "री-प्राइस स्टिकर" : "Sticker or Barcode"}
                  </span>
                </div>
              )}

              {isScanning && (
                <button
                  onClick={() => captureCurrentFrameToSlot("barcode")}
                  className="btn-gov-secondary"
                  style={{ fontSize: "0.75rem", padding: "0.35rem 0.6rem", width: "100%", justifyContent: "center" }}
                >
                  <Camera size={13} />
                  <span>{lang === "hi" ? "स्टिकर कैप्चर करें" : "Snap Sticker"}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

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

        {/* Targeted Horizontal 1D Barcode Aiming Reticle with Red Laser */}
        {isScanning && !isProcessing && scanStatus !== "detected" && (
          <div className="scan-reticle-box">
            <div style={{ fontSize: "0.68rem", color: "#38bdf8", fontWeight: 700, letterSpacing: "0.5px", textTransform: "uppercase" }}>
              {lang === "hi" ? "बारकोड को इस बॉक्स में रखें" : "Align 1D Barcode Here"}
            </div>
            <div className="scan-laser-line-horizontal" />
            <div style={{ fontSize: "0.62rem", color: "#cbd5e1", fontFamily: "var(--font-mono)" }}>
              EAN-13 • UPC • CODE 128
            </div>
          </div>
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
            {hasTorch && isScanning && (
              <button
                onClick={toggleTorch}
                title={isTorchOn ? "Turn Off Flashlight" : "Turn On Flashlight"}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  background: isTorchOn ? "#f59e0b" : "rgba(15, 23, 42, 0.85)",
                  color: isTorchOn ? "#0f172a" : "#f59e0b",
                  border: "1px solid #f59e0b",
                  padding: "0.25rem 0.55rem",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.72rem",
                  fontWeight: 700,
                }}
              >
                {isTorchOn ? <ZapOff size={13} /> : <Zap size={13} />}
                <span>{isTorchOn ? "Torch On" : "Torch"}</span>
              </button>
            )}

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
        {!isMultiShotMode && !isScanning && !isProcessing && (
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

        {!isMultiShotMode && isScanning && (
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

        {/* Multi-Shot Mode Controls */}
        {isMultiShotMode && !isScanning && !isProcessing && (
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
              <span>{lang === "hi" ? "पैनल कैप्चर हेतु कैमरा खोलें" : "Open Camera to Capture Panels"}</span>
            </button>

            {capturedSlotsCount > 0 && (
              <>
                <button
                  onClick={handleExecuteMultiShotAudit}
                  disabled={isProcessing}
                  className="btn-gov-primary"
                  style={{
                    padding: "0.75rem 1.75rem",
                    fontSize: "0.92rem",
                    background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                    boxShadow: "0 0 20px rgba(16, 185, 129, 0.4)",
                  }}
                >
                  <Layers size={18} />
                  <span>
                    {lang === "hi"
                      ? `मल्टी-शॉट ऑडिट (${capturedSlotsCount}/3 पैनल)`
                      : `Audit Multi-Shot Packaging (${capturedSlotsCount}/3 Panels)`}
                  </span>
                </button>

                <button
                  onClick={resetAllSlots}
                  className="btn-gov-secondary"
                  style={{ padding: "0.75rem 1.25rem", fontSize: "0.92rem" }}
                  title="Clear all captured packaging panels"
                >
                  <Trash2 size={16} color="#ef4444" />
                  <span>{lang === "hi" ? "पैनल साफ़ करें" : "Reset Panels"}</span>
                </button>
              </>
            )}
          </>
        )}

        {isMultiShotMode && isScanning && (
          <>
            <button
              onClick={handleExecuteMultiShotAudit}
              disabled={isProcessing || capturedSlotsCount === 0}
              className="btn-gov-primary"
              style={{
                padding: "0.75rem 1.75rem",
                fontSize: "0.92rem",
                background: capturedSlotsCount > 0 ? "linear-gradient(135deg, #10b981 0%, #059669 100%)" : "#64748b",
                boxShadow: capturedSlotsCount > 0 ? "0 0 20px rgba(16, 185, 129, 0.4)" : "none",
                cursor: capturedSlotsCount > 0 ? "pointer" : "not-allowed",
              }}
            >
              <Layers size={18} />
              <span>
                {lang === "hi"
                  ? `ऑडिट प्रारंभ करें (${capturedSlotsCount}/3)`
                  : `Execute Multi-Shot Audit (${capturedSlotsCount}/3)`}
              </span>
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
