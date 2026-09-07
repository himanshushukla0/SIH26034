import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { Upload, Camera, Image, Sparkles, FileText } from "lucide-react";

interface ImageUploaderProps {
  onFileSelect: (file: File) => void;
  isLoading: boolean;
}

/** Pre-rendered high-resolution mock label generator for 1-click evaluation. */
async function generateSamplePackaging(type: "compliant" | "violation"): Promise<File> {
  const canvas = document.createElement("canvas");
  canvas.width = 1000;
  canvas.height = 750;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas context failed");

  // Official government packaging mock canvas
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

  // Outer border & decorative packaging frame
  ctx.strokeStyle = type === "compliant" ? "#003366" : "#dc2626";
  ctx.lineWidth = 6;
  ctx.strokeRect(30, 30, 940, 690);

  ctx.strokeStyle = "rgba(0, 51, 102, 0.2)";
  ctx.lineWidth = 1;
  ctx.strokeRect(40, 40, 920, 670);

  // Header / Brand Title
  ctx.fillStyle = "#003366";
  ctx.font = "bold 44px 'Segoe UI', Arial, sans-serif";
  const title = type === "compliant" ? "TATA TEA GOLD 500g" : "IMPORTED CHOCO CRUNCH 300g";
  ctx.fillText(title, 60, 105);

  ctx.fillStyle = "#0284c7";
  ctx.font = "bold 22px 'Segoe UI', Arial, sans-serif";
  ctx.fillText("PRINCIPAL DISPLAY PANEL (PDP) — STATUTORY DECLARATION", 60, 150);

  // Declaration text lines
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

  // Barcode Mockup
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

export default function ImageUploader({ onFileSelect, isLoading }: ImageUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith("image/")) return;
      setPreview(URL.createObjectURL(file));
      onFileSelect(file);
    },
    [onFileSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleClick = () => {
    if (!isLoading) fileInputRef.current?.click();
  };

  const handleQuickSample = async (type: "compliant" | "violation") => {
    const file = await generateSamplePackaging(type);
    handleFile(file);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={{ maxWidth: "800px", margin: "0 auto" }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleInputChange}
        style={{ display: "none" }}
        id="image-upload-input"
      />

      {preview ? (
        <div className="glass-card" style={{ padding: "var(--space-lg)" }}>
          <div style={{ position: "relative" }}>
            <img
              src={preview}
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
                  setPreview(null);
                  handleClick();
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
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div
            className={`upload-zone glass-card ${isDragging ? "drag-active" : ""}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={handleClick}
            role="button"
            tabIndex={0}
            id="image-drop-zone"
            style={{
              padding: "3rem 2rem",
              cursor: "pointer",
              border: isDragging
                ? "2px dashed var(--gov-navy)"
                : "2px dashed var(--gov-navy-light)",
              background: isDragging
                ? "#eff6ff"
                : "#ffffff",
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
            <div className="upload-zone-title" style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--gov-navy-dark)" }}>
              {isDragging ? "Drop packaging photo here" : "Upload Packaging Photo for Multimodal OCR"}
            </div>
            <div className="upload-zone-subtitle" style={{ fontSize: "0.88rem", color: "var(--text-secondary)", marginTop: "0.4rem" }}>
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
                onClick={() => handleQuickSample("compliant")}
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
                onClick={() => handleQuickSample("violation")}
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
        </div>
      )}
    </motion.div>
  );
}
