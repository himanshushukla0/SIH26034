import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Upload,
  Camera,
  Image,
  Sparkles,
  FileText,
  Layers,
  CheckCircle2,
  Trash2,
  Tag,
  Barcode as BarcodeIcon,
} from "lucide-react";
import type { MultiShotFiles } from "../api";

interface ImageUploaderProps {
  onFileSelect: (file: File) => void;
  onMultiShotSelect?: (shots: MultiShotFiles) => void;
  isLoading: boolean;
}

/** Pre-rendered high-resolution mock label generator for 1-click single evaluation. */
async function generateSamplePackaging(type: "compliant" | "violation"): Promise<File> {
  const canvas = document.createElement("canvas");
  canvas.width = 1000;
  canvas.height = 750;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas context failed");

  const bgGrad = ctx.createLinearGradient(0, 0, 1000, 750);
  if (type === "compliant") {
    bgGrad.addColorStop(0, "#f8fafc");
    bgGrad.addColorStop(1, "#f1f5f9");
  } else {
    bgGrad.addColorStop(0, "#fff5f5");
    bgGrad.addColorStop(1, "#fee2e2");
  }
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, 1000, 750);

  ctx.strokeStyle = type === "compliant" ? "#003366" : "#dc2626";
  ctx.lineWidth = 6;
  ctx.strokeRect(30, 30, 940, 690);

  ctx.fillStyle = "#003366";
  ctx.font = "bold 44px 'Segoe UI', Arial, sans-serif";
  const title = type === "compliant" ? "TATA TEA GOLD 500g" : "IMPORTED CHOCO CRUNCH 300g";
  ctx.fillText(title, 60, 105);

  ctx.fillStyle = "#0284c7";
  ctx.font = "bold 22px 'Segoe UI', Arial, sans-serif";
  ctx.fillText("PRINCIPAL DISPLAY PANEL (PDP) — STATUTORY DECLARATION", 60, 150);

  ctx.fillStyle = "#0f172a";
  ctx.font = "22px 'Segoe UI', Arial, sans-serif";
  let y = 205;
  const step = 42;

  const lines =
    type === "compliant"
      ? [
          "1. Generic Name: Premium Black Tea",
          "2. Manufacturer: Tata Consumer Products Limited, 1 Bishop Lefroy Road, Kolkata 700020",
          "3. Country of Origin: India",
          "4. Net Quantity: 500 g",
          "5. Month & Year of Packing: 08/2026",
          "6. Best Before: 12 months from packaging date",
          "7. Maximum Retail Price (MRP): Rs. 320.00 (Inclusive of all taxes)",
          "8. Unit Sale Price (USP): Rs. 0.64 / g",
          "9. Consumer Care: Toll Free 1800-108-4488 | care@tataconsumer.com",
          "10. FSSAI License No.: 10014031001025",
        ]
      : [
          "1. Generic Name: Chocolate Wafers",
          "2. Manufacturer: Global Snacks Corp (Address omitted)",
          "3. Country of Origin: (Missing declaration)",
          "4. Net Quantity: 300 gms (Non-standard SI unit)",
          "5. Month & Year of Mfg: 01/2025",
          "6. Best Before: 06/2025 (Expired)",
          "7. Maximum Retail Price (MRP): Rs. 250.00 (Taxes not stated)",
          "8. Unit Sale Price (USP): (Missing USP declaration)",
          "9. Consumer Care: (Missing grievance details)",
          "10. FSSAI License No.: 10012000000001 (Fabricated State Code 00)",
        ];

  for (const line of lines) {
    ctx.fillText(line, 60, y);
    y += step;
  }

  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = 2;
  ctx.fillRect(680, 560, 260, 110);
  ctx.strokeRect(680, 560, 260, 110);
  ctx.fillStyle = "#000000";
  ctx.font = "bold 26px monospace";
  ctx.fillText("||| || |||| |||", 700, 620);
  ctx.font = "16px monospace";
  ctx.fillText(type === "compliant" ? "8901030383478" : "8909999999999", 735, 650);

  return new Promise((resolve) => {
    canvas.toBlob(
      (blob) => {
        resolve(
          new File([blob!], `${type}_sample_packaging.jpg`, {
            type: "image/jpeg",
          })
        );
      },
      "image/jpeg",
      0.95
    );
  });
}

/** Pre-render multi-shot packaging panels for 1-click evaluation. */
async function generateMultiShotPreset(
  preset: "tea_split" | "reprice_sticker" | "narrow_biscuit"
): Promise<{ front: File; back: File; barcode: File }> {
  const makeCanvas = (
    title: string,
    subtitle: string,
    lines: string[],
    badgeText?: string,
    badgeColor?: string
  ): Promise<File> => {
    const canvas = document.createElement("canvas");
    canvas.width = 900;
    canvas.height = 650;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas context failed");

    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, 900, 650);

    ctx.strokeStyle = "#003366";
    ctx.lineWidth = 5;
    ctx.strokeRect(20, 20, 860, 610);

    ctx.fillStyle = "#003366";
    ctx.font = "bold 36px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(title, 45, 80);

    ctx.fillStyle = "#0284c7";
    ctx.font = "bold 18px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(subtitle, 45, 115);

    if (badgeText) {
      ctx.fillStyle = badgeColor || "#d97706";
      ctx.fillRect(45, 135, 340, 32);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 15px monospace";
      ctx.fillText(badgeText, 55, 157);
    }

    ctx.fillStyle = "#0f172a";
    ctx.font = "20px 'Segoe UI', Arial, sans-serif";
    let y = badgeText ? 205 : 170;
    for (const line of lines) {
      ctx.fillText(line, 45, y);
      y += 38;
    }

    return new Promise((resolve) => {
      canvas.toBlob(
        (blob) => {
          resolve(
            new File([blob!], `${title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}.jpg`, {
              type: "image/jpeg",
            })
          );
        },
        "image/jpeg",
        0.95
      );
    });
  };

  if (preset === "tea_split") {
    const front = await makeCanvas(
      "TATA TEA GOLD (FRONT PANEL)",
      "PRINCIPAL DISPLAY PANEL — BRAND & HEADLINE DECLARATIONS",
      [
        "Brand: TATA TEA GOLD",
        "Net Weight: 500 g",
        "MRP (incl. of all taxes): Rs. 320.00",
        "Unit Sale Price: Rs. 0.64 / g",
        "100% Pure Indian Tea Leaves",
      ],
      "FRONT PDP: HEADLINE MRP & NET QTY",
      "#0284c7"
    );

    const back = await makeCanvas(
      "TATA TEA GOLD (BACK PANEL)",
      "STATUTORY DECLARATIONS BLOCK (RULE 6 COMPLIANCE)",
      [
        "Mfd. by: Tata Consumer Products Limited",
        "Address: 1 Bishop Lefroy Road, Kolkata 700020",
        "Month & Year of Packing: 08/2026",
        "Best Before: 12 months from packing date",
        "Country of Origin: India",
        "Consumer Care: 1800-108-4488 | care@tataconsumer.com",
        "FSSAI License No: 10014031001025",
      ],
      "BACK PANEL: LEGAL METROLOGY BLOCK",
      "#15803d"
    );

    const barcode = await makeCanvas(
      "RETAIL BARCODE CLOSE-UP",
      "1D EAN-13 RETRIEVAL & GS1 AUTHENTICITY",
      [
        "EAN-13: 8901030383478",
        "Country Identifier: 890 (GS1 India Registered)",
        "Batch: BLK-2026-A8",
        "Standard Printed Packaging",
      ],
      "BARCODE PANEL: GS1 COMPLIANT",
      "#475569"
    );

    return { front, back, barcode };
  } else if (preset === "reprice_sticker") {
    const front = await makeCanvas(
      "PREMIUM HAZELNUT SPREAD (FRONT)",
      "FRONT BRAND PANEL",
      [
        "Brand: Artisanal Hazelnut Cocoa Spread",
        "Net Weight: 350 g",
        "Original Printed MRP: Rs. 200.00 (Inclusive of all taxes)",
        "Imported Confectionery",
      ],
      "FRONT PANEL: PRINTED MRP RS 200",
      "#0284c7"
    );

    const back = await makeCanvas(
      "PREMIUM HAZELNUT SPREAD (BACK)",
      "STATUTORY DECLARATIONS PANEL",
      [
        "Imported & Packed by: Global Gourmet Ltd",
        "Andheri East, Mumbai 400069",
        "Country of Origin: Switzerland",
        "Mfg Date: 02/2026 | Best Before: 12 months",
        "Customer Care: support@globalgourmet.in",
      ],
      "BACK PANEL: DECLARATIONS",
      "#15803d"
    );

    const barcode = await makeCanvas(
      "STICKER OVER-PRINT CLOSE-UP",
      "ALTERATION OF RETAIL PRICE (SECTION 18 CONTRAVENTION)",
      [
        "OVER-STICKER DETECTED:",
        "Sticker Price: Rs. 260.00",
        "Underlying Printed MRP: Rs. 200.00",
        "Contravening Rule 18(2) & Section 36(1)",
        "Dual Pricing Sticker Pasted Over Printed Packaging",
      ],
      "SECTION 18 CONTRAVENTION: DUAL PRICING",
      "#b91c1c"
    );

    return { front, back, barcode };
  } else {
    const front = await makeCanvas(
      "NARROW BISCUIT PACK (FRONT)",
      "SPLIT LINE PAIR SCANNING DEMONSTRATION",
      [
        "Brand: Golden Wheat Biscuits",
        "Net Wt.",
        "lOOO ml",
        "MRP (incl. of all taxes)",
        "Rs. 2SO.OO",
      ],
      "PASS 2 STITCHED LINES & SCOPED REPAIR",
      "#d97706"
    );

    const back = await makeCanvas(
      "NARROW BISCUIT PACK (BACK)",
      "DECLARATION BLOCK — SCOPED REPAIR & PIN CODE SWEEP",
      [
        "Packed on",
        "05/2026",
        "Best Before: 9 months",
        "Gupta Oil Mills, Sector 4, Mumbai 400001",
        "Country of Origin: India",
        "Customer Care: 9876543210",
      ],
      "SCOPED REPAIR: GUPTA SURVIVES, PIN DETECTED",
      "#15803d"
    );

    const barcode = await makeCanvas(
      "BISCUIT 1D BARCODE",
      "RETAIL SCANNER CLOSE-UP",
      ["EAN-13: 8901234567890", "Compact Retail Strip", "Batch: GWB-99"],
      "1D BARCODE CLOSE-UP",
      "#475569"
    );

    return { front, back, barcode };
  }
}

export default function ImageUploader({
  onFileSelect,
  onMultiShotSelect,
  isLoading,
}: ImageUploaderProps) {
  const [activeMode, setActiveMode] = useState<"single" | "multishot">("multishot");

  // Single-shot state
  const [isDragging, setIsDragging] = useState(false);
  const [singlePreview, setSinglePreview] = useState<string | null>(null);
  const singleInputRef = useRef<HTMLInputElement>(null);

  // Multi-shot state
  const [shots, setShots] = useState<MultiShotFiles>({
    front: null,
    back: null,
    barcode: null,
  });
  const [previews, setPreviews] = useState<{
    front: string | null;
    back: string | null;
    barcode: string | null;
  }>({
    front: null,
    back: null,
    barcode: null,
  });

  const frontInputRef = useRef<HTMLInputElement>(null);
  const backInputRef = useRef<HTMLInputElement>(null);
  const barcodeInputRef = useRef<HTMLInputElement>(null);

  const handleSingleFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith("image/")) return;
      setSinglePreview(URL.createObjectURL(file));
      onFileSelect(file);
    },
    [onFileSelect]
  );

  const handleSingleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleSingleFile(file);
    },
    [handleSingleFile]
  );

  const handleMultiShotSlot = (panel: "front" | "back" | "barcode", file: File) => {
    if (!file.type.startsWith("image/")) return;
    const previewUrl = URL.createObjectURL(file);
    setShots((prev) => ({ ...prev, [panel]: file }));
    setPreviews((prev) => ({ ...prev, [panel]: previewUrl }));
  };

  const removeMultiShotSlot = (panel: "front" | "back" | "barcode") => {
    setShots((prev) => ({ ...prev, [panel]: null }));
    setPreviews((prev) => ({ ...prev, [panel]: null }));
  };

  const capturedCount = [shots.front, shots.back, shots.barcode].filter(Boolean).length;

  const handleTriggerMultiShotAudit = () => {
    if (capturedCount === 0 || !onMultiShotSelect) return;
    onMultiShotSelect(shots);
  };

  const handleApplyMultiShotPreset = async (
    preset: "tea_split" | "reprice_sticker" | "narrow_biscuit"
  ) => {
    const mockShots = await generateMultiShotPreset(preset);
    const frontUrl = URL.createObjectURL(mockShots.front);
    const backUrl = URL.createObjectURL(mockShots.back);
    const barcodeUrl = URL.createObjectURL(mockShots.barcode);

    setShots(mockShots);
    setPreviews({
      front: frontUrl,
      back: backUrl,
      barcode: barcodeUrl,
    });

    if (onMultiShotSelect) {
      onMultiShotSelect(mockShots);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={{ maxWidth: "860px", margin: "0 auto" }}
    >
      <input
        ref={singleInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleSingleFile(file);
        }}
        style={{ display: "none" }}
      />

      <input
        ref={frontInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleMultiShotSlot("front", file);
        }}
        style={{ display: "none" }}
      />
      <input
        ref={backInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleMultiShotSlot("back", file);
        }}
        style={{ display: "none" }}
      />
      <input
        ref={barcodeInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleMultiShotSlot("barcode", file);
        }}
        style={{ display: "none" }}
      />

      {/* Mode Selector Toggle */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: "8px",
          marginBottom: "1.5rem",
          background: "rgba(255, 255, 255, 0.06)",
          padding: "5px",
          borderRadius: "10px",
          border: "1px solid var(--border)",
          maxWidth: "540px",
          margin: "0 auto 1.5rem auto",
        }}
      >
        <button
          type="button"
          onClick={() => setActiveMode("multishot")}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
            padding: "8px 16px",
            borderRadius: "7px",
            fontSize: "0.85rem",
            fontWeight: 700,
            cursor: "pointer",
            transition: "all 0.2s ease",
            border: "none",
            background:
              activeMode === "multishot"
                ? "var(--gov-navy, #003366)"
                : "transparent",
            color: activeMode === "multishot" ? "#ffffff" : "var(--text-muted)",
            boxShadow:
              activeMode === "multishot"
                ? "0 2px 10px rgba(0, 51, 102, 0.35)"
                : "none",
          }}
        >
          <Layers size={16} />
          <span>Multi-Shot (Front + Back)</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveMode("single")}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
            padding: "8px 16px",
            borderRadius: "7px",
            fontSize: "0.85rem",
            fontWeight: 700,
            cursor: "pointer",
            transition: "all 0.2s ease",
            border: "none",
            background:
              activeMode === "single"
                ? "var(--gov-navy, #003366)"
                : "transparent",
            color: activeMode === "single" ? "#ffffff" : "var(--text-muted)",
            boxShadow:
              activeMode === "single"
                ? "0 2px 10px rgba(0, 51, 102, 0.35)"
                : "none",
          }}
        >
          <Camera size={16} />
          <span>Single Label Photo</span>
        </button>
      </div>

      {/* MODE 1: MULTI-SHOT CAPTURE */}
      {activeMode === "multishot" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div
            style={{
              padding: "0.9rem 1.25rem",
              background: "rgba(56, 189, 248, 0.08)",
              border: "1px solid rgba(56, 189, 248, 0.25)",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <Layers size={22} color="#38bdf8" style={{ flexShrink: 0 }} />
            <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>
              <strong style={{ color: "#ffffff" }}>Physical Packaging Reality: </strong>
              MRP is often printed on the front, statutory declarations on the back, and re-priced
              stickers over barcodes. Capture up to 3 panels to audit as <strong>one unified label</strong>.
            </div>
          </div>

          {/* 3 Dedicated Packaging Slots */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "1rem" }}>
            {/* Slot 1: Front Panel (PDP) */}
            <div
              className="glass-card"
              style={{
                padding: "1.25rem",
                borderRadius: "10px",
                border: previews.front ? "2px solid #10b981" : "1px dashed var(--border)",
                display: "flex",
                flexDirection: "column",
                position: "relative",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <Image size={18} color="#38bdf8" />
                  <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "#ffffff" }}>
                    1. Front Panel (PDP)
                  </span>
                </div>
                {previews.front ? (
                  <span style={{ fontSize: "0.72rem", color: "#10b981", fontWeight: 700, display: "flex", alignItems: "center", gap: "3px" }}>
                    <CheckCircle2 size={13} /> Loaded
                  </span>
                ) : (
                  <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Recommended</span>
                )}
              </div>

              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: "0 0 12px 0" }}>
                Brand title, product imagery, net quantity, and front headline MRP.
              </p>

              {previews.front ? (
                <div style={{ position: "relative", borderRadius: "8px", overflow: "hidden", height: "180px", background: "#000" }}>
                  <img src={previews.front} alt="Front panel" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  <button
                    type="button"
                    onClick={() => removeMultiShotSlot("front")}
                    style={{
                      position: "absolute",
                      top: "6px",
                      right: "6px",
                      background: "rgba(0,0,0,0.65)",
                      border: "none",
                      color: "#ef4444",
                      padding: "5px",
                      borderRadius: "6px",
                      cursor: "pointer",
                    }}
                    title="Remove Front Panel"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => frontInputRef.current?.click()}
                  style={{
                    height: "180px",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.03)",
                    border: "1px dashed var(--border)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                    cursor: "pointer",
                  }}
                >
                  <Upload size={24} color="var(--text-muted)" />
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Add Front Photo</span>
                </div>
              )}
            </div>

            {/* Slot 2: Back / Side Declarations Panel */}
            <div
              className="glass-card"
              style={{
                padding: "1.25rem",
                borderRadius: "10px",
                border: previews.back ? "2px solid #10b981" : "1px dashed var(--border)",
                display: "flex",
                flexDirection: "column",
                position: "relative",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <FileText size={18} color="#a855f7" />
                  <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "#ffffff" }}>
                    2. Back Declarations
                  </span>
                </div>
                {previews.back ? (
                  <span style={{ fontSize: "0.72rem", color: "#10b981", fontWeight: 700, display: "flex", alignItems: "center", gap: "3px" }}>
                    <CheckCircle2 size={13} /> Loaded
                  </span>
                ) : (
                  <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Recommended</span>
                )}
              </div>

              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: "0 0 12px 0" }}>
                Mfd. by address with PIN, Packing Month/Year, Best Before, Consumer Care.
              </p>

              {previews.back ? (
                <div style={{ position: "relative", borderRadius: "8px", overflow: "hidden", height: "180px", background: "#000" }}>
                  <img src={previews.back} alt="Back panel" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  <button
                    type="button"
                    onClick={() => removeMultiShotSlot("back")}
                    style={{
                      position: "absolute",
                      top: "6px",
                      right: "6px",
                      background: "rgba(0,0,0,0.65)",
                      border: "none",
                      color: "#ef4444",
                      padding: "5px",
                      borderRadius: "6px",
                      cursor: "pointer",
                    }}
                    title="Remove Back Panel"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => backInputRef.current?.click()}
                  style={{
                    height: "180px",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.03)",
                    border: "1px dashed var(--border)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                    cursor: "pointer",
                  }}
                >
                  <Upload size={24} color="var(--text-muted)" />
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Add Back Photo</span>
                </div>
              )}
            </div>

            {/* Slot 3: Barcode / Price Sticker Close-Up */}
            <div
              className="glass-card"
              style={{
                padding: "1.25rem",
                borderRadius: "10px",
                border: previews.barcode ? "2px solid #10b981" : "1px dashed var(--border)",
                display: "flex",
                flexDirection: "column",
                position: "relative",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <BarcodeIcon size={18} color="#f59e0b" />
                  <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "#ffffff" }}>
                    3. Barcode / Sticker
                  </span>
                </div>
                {previews.barcode ? (
                  <span style={{ fontSize: "0.72rem", color: "#10b981", fontWeight: 700, display: "flex", alignItems: "center", gap: "3px" }}>
                    <CheckCircle2 size={13} /> Loaded
                  </span>
                ) : (
                  <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Optional</span>
                )}
              </div>

              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: "0 0 12px 0" }}>
                1D EAN-13 barcode or altered / re-priced sticker over printed MRP.
              </p>

              {previews.barcode ? (
                <div style={{ position: "relative", borderRadius: "8px", overflow: "hidden", height: "180px", background: "#000" }}>
                  <img src={previews.barcode} alt="Barcode close-up" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  <button
                    type="button"
                    onClick={() => removeMultiShotSlot("barcode")}
                    style={{
                      position: "absolute",
                      top: "6px",
                      right: "6px",
                      background: "rgba(0,0,0,0.65)",
                      border: "none",
                      color: "#ef4444",
                      padding: "5px",
                      borderRadius: "6px",
                      cursor: "pointer",
                    }}
                    title="Remove Barcode Close-Up"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => barcodeInputRef.current?.click()}
                  style={{
                    height: "180px",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.03)",
                    border: "1px dashed var(--border)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                    cursor: "pointer",
                  }}
                >
                  <Upload size={24} color="var(--text-muted)" />
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Add Barcode Photo</span>
                </div>
              )}
            </div>
          </div>

          {/* Unified Multi-Shot Audit Trigger Button */}
          <div style={{ textAlign: "center", marginTop: "0.5rem" }}>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleTriggerMultiShotAudit}
              disabled={capturedCount === 0 || isLoading}
              className="btn-gov-primary"
              style={{
                padding: "0.85rem 2.5rem",
                fontSize: "1rem",
                fontWeight: 700,
                opacity: capturedCount === 0 || isLoading ? 0.45 : 1,
                cursor: capturedCount === 0 || isLoading ? "not-allowed" : "pointer",
                boxShadow: "0 4px 20px rgba(0, 51, 102, 0.4)",
              }}
            >
              <Sparkles size={18} />
              <span>
                Audit Unified Multi-Shot Packaging ({capturedCount}/3 Panels Captured)
              </span>
            </motion.button>
          </div>

          {/* Multi-Shot 1-Click Simulation Presets */}
          <div
            style={{
              padding: "1.1rem 1.25rem",
              borderRadius: "10px",
              background: "#ffffff",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow-card)",
              marginTop: "0.75rem",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                fontSize: "0.8rem",
                fontWeight: 700,
                color: "var(--gov-navy)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "0.75rem",
              }}
            >
              <Sparkles size={15} color="#d97706" />
              <span>Instant Multi-Shot Test Presets (Zero File Upload Needed):</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0.75rem" }}>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleApplyMultiShotPreset("tea_split")}
                className="demo-chip"
                type="button"
                style={{
                  padding: "0.85rem 1rem",
                  border: "1px solid #86efac",
                  background: "#f0fdf4",
                  borderRadius: "8px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.65rem",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <Layers size={18} color="#15803d" style={{ marginTop: "2px", flexShrink: 0 }} />
                <div>
                  <div style={{ fontWeight: 700, color: "#15803d", fontSize: "0.82rem" }}>
                    Preset A: Split Tea Pack
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "#475569", marginTop: "2px" }}>
                    Front MRP + Back Declarations (89% Stage 1 Screener settlement)
                  </div>
                </div>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleApplyMultiShotPreset("reprice_sticker")}
                className="demo-chip"
                type="button"
                style={{
                  padding: "0.85rem 1rem",
                  border: "1px solid #fca5a5",
                  background: "#fef2f2",
                  borderRadius: "8px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.65rem",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <Tag size={18} color="#b91c1c" style={{ marginTop: "2px", flexShrink: 0 }} />
                <div>
                  <div style={{ fontWeight: 700, color: "#b91c1c", fontSize: "0.82rem" }}>
                    Preset B: Re-Priced Over-Sticker
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "#475569", marginTop: "2px" }}>
                    Printed Rs. 200 vs Sticker Rs. 260 (Sec 18 Alteration)
                  </div>
                </div>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleApplyMultiShotPreset("narrow_biscuit")}
                className="demo-chip"
                type="button"
                style={{
                  padding: "0.85rem 1rem",
                  border: "1px solid #fde68a",
                  background: "#fffbeb",
                  borderRadius: "8px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.65rem",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <Sparkles size={18} color="#d97706" style={{ marginTop: "2px", flexShrink: 0 }} />
                <div>
                  <div style={{ fontWeight: 700, color: "#b45309", fontSize: "0.82rem" }}>
                    Preset C: Narrow Biscuit Pack
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "#475569", marginTop: "2px" }}>
                    Split line pairs stitched (conf 0.82) + Scoped repair
                  </div>
                </div>
              </motion.button>
            </div>
          </div>
        </div>
      )}

      {/* MODE 2: SINGLE PHOTO UPLOAD */}
      {activeMode === "single" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {singlePreview ? (
            <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
              <div style={{ position: "relative" }}>
                <img
                  src={singlePreview}
                  alt="Uploaded packaging"
                  className="image-preview"
                  style={{
                    width: "100%",
                    maxHeight: "450px",
                    objectFit: "contain",
                    borderRadius: "8px",
                    border: "1px solid var(--border)",
                  }}
                />
                {!isLoading && (
                  <motion.button
                    className="btn btn-outline"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSinglePreview(null);
                      singleInputRef.current?.click();
                    }}
                    style={{
                      position: "absolute",
                      top: "var(--space-md)",
                      right: "var(--space-md)",
                      background: "#ffffff",
                      color: "var(--gov-navy)",
                      border: "1px solid var(--gov-navy)",
                      boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
                    }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Image size={16} />
                    Change Image
                  </motion.button>
                )}
              </div>
            </div>
          ) : (
            <>
              <div
                className={`upload-zone glass-card ${isDragging ? "drag-active" : ""}`}
                onDrop={handleSingleDrop}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onClick={() => {
                  if (!isLoading) singleInputRef.current?.click();
                }}
                role="button"
                tabIndex={0}
                id="image-drop-zone"
                style={{
                  padding: "3rem 2rem",
                  cursor: "pointer",
                  border: isDragging
                    ? "2px dashed var(--gov-navy)"
                    : "2px dashed var(--gov-navy-light)",
                  background: isDragging ? "#eff6ff" : "#ffffff",
                  boxShadow: isDragging
                    ? "0 4px 20px rgba(0, 51, 102, 0.15)"
                    : "var(--shadow-card)",
                  borderRadius: "10px",
                  textAlign: "center",
                }}
              >
                <motion.div
                  className="upload-zone-icon"
                  animate={{ y: isDragging ? -8 : 0 }}
                  transition={{ type: "spring", stiffness: 300 }}
                  style={{
                    width: "68px",
                    height: "68px",
                    borderRadius: "12px",
                    background: "#eff6ff",
                    border: "1px solid #bfdbfe",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 1.25rem",
                    color: "var(--gov-navy)",
                  }}
                >
                  {isDragging ? <Camera size={34} /> : <Upload size={34} />}
                </motion.div>
                <div
                  className="upload-zone-title"
                  style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--gov-navy-dark)" }}
                >
                  {isDragging ? "Drop packaging photo here" : "Upload Packaging Photo for Multimodal OCR"}
                </div>
                <div
                  className="upload-zone-subtitle"
                  style={{ fontSize: "0.88rem", color: "var(--text-secondary)", marginTop: "0.4rem" }}
                >
                  Drag & drop market raid packaging labels or click to browse.
                  <br />
                  Supports JPEG, PNG, WebP — evaluated directly under Legal Metrology Rules, 2011.
                </div>
              </div>

              {/* Quick Sample Presets */}
              <div
                style={{
                  padding: "1.1rem 1.25rem",
                  borderRadius: "10px",
                  background: "#ffffff",
                  border: "1px solid var(--border)",
                  boxShadow: "var(--shadow-card)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    fontSize: "0.8rem",
                    fontWeight: 700,
                    color: "var(--gov-navy)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    marginBottom: "0.75rem",
                  }}
                >
                  <Sparkles size={15} color="#d97706" />
                  <span>Instant Test Samples (No File Upload Needed):</span>
                </div>

                <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={async () => {
                      const file = await generateSamplePackaging("compliant");
                      handleSingleFile(file);
                    }}
                    className="demo-chip"
                    type="button"
                    style={{
                      flex: 1,
                      minWidth: "220px",
                      padding: "0.85rem 1rem",
                      border: "1px solid #86efac",
                      background: "#f0fdf4",
                      borderRadius: "8px",
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "0.75rem",
                      cursor: "pointer",
                      textAlign: "left",
                    }}
                  >
                    <FileText size={20} color="#15803d" style={{ marginTop: "2px", flexShrink: 0 }} />
                    <div>
                      <div style={{ fontWeight: 700, color: "#15803d", fontSize: "0.85rem" }}>
                        Sample A: Fully Compliant Label
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "#475569", marginTop: "2px" }}>
                        Tata Tea Gold 500g (All 10 rules passed)
                      </div>
                    </div>
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={async () => {
                      const file = await generateSamplePackaging("violation");
                      handleSingleFile(file);
                    }}
                    className="demo-chip"
                    type="button"
                    style={{
                      flex: 1,
                      minWidth: "220px",
                      padding: "0.85rem 1rem",
                      border: "1px solid #fca5a5",
                      background: "#fef2f2",
                      borderRadius: "8px",
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "0.75rem",
                      cursor: "pointer",
                      textAlign: "left",
                    }}
                  >
                    <FileText size={20} color="#b91c1c" style={{ marginTop: "2px", flexShrink: 0 }} />
                    <div>
                      <div style={{ fontWeight: 700, color: "#b91c1c", fontSize: "0.85rem" }}>
                        Sample B: Violation & Tampered Label
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "#475569", marginTop: "2px" }}>
                        Choco Crunch (Missing USP, fake FSSAI, expired)
                      </div>
                    </div>
                  </motion.button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </motion.div>
  );
}
