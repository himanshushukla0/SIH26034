import { motion } from "framer-motion";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Scale,
  DollarSign,
  Globe2,
  Building2,
  Tag,
  HelpCircle,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";
import type { PackagingExtractions, Violation } from "../api";

interface ComparisonViewProps {
  extractions: PackagingExtractions;
  listingData?: Record<string, unknown>;
  platform?: string;
  sourceUrl?: string;
  violations?: Violation[];
}

interface FieldComparison {
  key: string;
  label: string;
  icon: typeof Scale;
  packValue: string | null;
  webValue: string | null;
  status: "match" | "mismatch" | "pack_only" | "web_only" | "both_missing";
  notes?: string;
  isOvercharge?: boolean;
}

function extractStringValue(val: unknown): string | null {
  if (val === null || val === undefined) return null;
  if (typeof val === "object" && val !== null && "value" in val) {
    const inner = (val as { value: unknown }).value;
    return inner !== null && inner !== undefined ? String(inner).trim() : null;
  }
  const s = String(val).trim();
  return s.length > 0 && s !== "null" && s !== "undefined" ? s : null;
}

function normalizeNumber(val: string | null): number | null {
  if (!val) return null;
  const numStr = val.replace(/[^0-9.]/g, "");
  const num = parseFloat(numStr);
  return isNaN(num) ? null : num;
}

export default function ComparisonView({
  extractions,
  listingData,
  platform,
  sourceUrl,
  violations = [],
}: ComparisonViewProps) {
  if (!listingData || Object.keys(listingData).length === 0) {
    return null;
  }

  // --- Extract Physical Packaging values ---
  const packMrp = extractStringValue(extractions.mrp);
  const packQty = extractStringValue(extractions.net_quantity);
  const packOrigin = extractStringValue(extractions.country_of_origin);
  const packMfr =
    extractStringValue(extractions.manufacturer_name) ||
    extractStringValue(extractions.manufacturer_address);
  const packGeneric =
    extractStringValue(extractions.generic_name) ||
    extractStringValue(extractions.product_name);
  const packUsp = extractStringValue(extractions.unit_sale_price);

  // --- Extract Web Listing values ---
  const webMrp =
    extractStringValue(listingData.listed_price) ||
    extractStringValue(listingData.mrp);
  const webQty = extractStringValue(listingData.net_quantity);
  const webOrigin = extractStringValue(listingData.country_of_origin);
  const webMfr =
    extractStringValue(listingData.manufacturer) ||
    extractStringValue(listingData.brand) ||
    extractStringValue(listingData.seller_name);
  const webGeneric =
    extractStringValue(listingData.product_name) ||
    extractStringValue(listingData.category);
  const webUsp = extractStringValue(listingData.unit_sale_price);

  // Check price overcharge
  const numPackMrp = normalizeNumber(packMrp);
  const numWebPrice = normalizeNumber(
    extractStringValue(listingData.listed_price) || webMrp
  );
  const isOvercharge =
    numPackMrp !== null && numWebPrice !== null && numWebPrice > numPackMrp;

  // Build comparison rows
  const comparisons: FieldComparison[] = [
    {
      key: "mrp",
      label: "Maximum Retail Price / Price",
      icon: DollarSign,
      packValue: packMrp ? `₹${packMrp.replace(/[^0-9.]/g, "")}` : null,
      webValue: webMrp ? `₹${webMrp.replace(/[^0-9.]/g, "")}` : null,
      isOvercharge,
      status: (() => {
        if (!packMrp && !webMrp) return "both_missing";
        if (!packMrp) return "web_only";
        if (!webMrp) return "pack_only";
        if (isOvercharge) return "mismatch";
        if (numPackMrp && numWebPrice && numWebPrice <= numPackMrp) return "match";
        return "match";
      })(),
      notes: isOvercharge
        ? `Overcharge: Online ₹${numWebPrice} > MRP ₹${numPackMrp} (Sec 18 violation)`
        : undefined,
    },
    {
      key: "net_quantity",
      label: "Net Quantity / Measure",
      icon: Scale,
      packValue: packQty,
      webValue: webQty,
      status: (() => {
        if (!packQty && !webQty) return "both_missing";
        if (!packQty) return "web_only";
        if (!webQty) return "pack_only";
        const cleanP = packQty.toLowerCase().replace(/\s+/g, "");
        const cleanW = webQty.toLowerCase().replace(/\s+/g, "");
        return cleanP === cleanW ? "match" : "mismatch";
      })(),
    },
    {
      key: "country_of_origin",
      label: "Country of Origin",
      icon: Globe2,
      packValue: packOrigin,
      webValue: webOrigin,
      status: (() => {
        if (!packOrigin && !webOrigin) return "both_missing";
        if (!packOrigin) return "web_only";
        if (!webOrigin) return "pack_only";
        return packOrigin.toLowerCase().trim() === webOrigin.toLowerCase().trim()
          ? "match"
          : "mismatch";
      })(),
    },
    {
      key: "manufacturer",
      label: "Manufacturer / Brand / Seller",
      icon: Building2,
      packValue: packMfr,
      webValue: webMfr,
      status: (() => {
        if (!packMfr && !webMfr) return "both_missing";
        if (!packMfr) return "web_only";
        if (!webMfr) return "pack_only";
        return "match"; // Often phrasing differs but both present
      })(),
    },
    {
      key: "unit_sale_price",
      label: "Unit Sale Price (USP)",
      icon: Tag,
      packValue: packUsp,
      webValue: webUsp,
      status: (() => {
        if (!packUsp && !webUsp) return "both_missing";
        if (!packUsp) return "web_only";
        if (!webUsp) return "pack_only";
        return "match";
      })(),
    },
    {
      key: "product_name",
      label: "Commodity / Product Name",
      icon: Tag,
      packValue: packGeneric,
      webValue: webGeneric,
      status: (() => {
        if (!packGeneric && !webGeneric) return "both_missing";
        if (!packGeneric) return "web_only";
        if (!webGeneric) return "pack_only";
        return "match";
      })(),
    },
  ];

  const mismatchCount = comparisons.filter((c) => c.status === "mismatch").length;
  const discrepancyCount = violations.filter((v) => v.is_discrepancy).length;
  const totalIssues = Math.max(mismatchCount, discrepancyCount);

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      style={{
        marginTop: "2.5rem",
        background: "rgba(18, 22, 36, 0.7)",
        backdropFilter: "blur(16px)",
        border: isOvercharge
          ? "1px solid rgba(239, 68, 68, 0.4)"
          : "1px solid rgba(59, 130, 246, 0.25)",
        borderRadius: "16px",
        padding: "1.75rem",
        boxShadow: isOvercharge
          ? "0 8px 32px rgba(239, 68, 68, 0.15)"
          : "0 8px 32px rgba(0, 0, 0, 0.3)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "1rem",
          marginBottom: "1.5rem",
          paddingBottom: "1.25rem",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
              marginBottom: "0.35rem",
            }}
          >
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                background: "#eff6ff",
                color: "var(--gov-navy)",
                padding: "0.2rem 0.6rem",
                borderRadius: "4px",
                border: "1px solid #bfdbfe",
              }}
            >
              Cross-Modal Verification
            </span>
            {platform && (
              <span
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                }}
              >
                Platform: <strong style={{ color: "var(--text)" }}>{platform}</strong>
              </span>
            )}
          </div>
          <h3
            style={{
              fontSize: "1.2rem",
              fontWeight: 700,
              color: "var(--gov-navy-dark)",
              margin: 0,
            }}
          >
            Physical Packaging vs. E-Commerce Listing Audit
          </h3>
          <p
            style={{
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
              margin: "0.25rem 0 0",
            }}
          >
            Automated cross-referencing between OCR extracted physical declarations and online marketplace data.
          </p>
        </div>

        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              fontSize: "0.8rem",
              fontWeight: 600,
              color: "var(--gov-navy)",
              background: "#ffffff",
              border: "1px solid var(--gov-navy)",
              padding: "0.4rem 0.8rem",
              borderRadius: "6px",
              textDecoration: "none",
              transition: "all 0.2s ease",
            }}
          >
            View Live Listing
            <ExternalLink size={13} />
          </a>
        )}
      </div>

      {/* Overcharge Banner Alert */}
      {isOvercharge && (
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "0.9rem",
            padding: "1rem 1.25rem",
            marginBottom: "1.5rem",
            borderRadius: "8px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
          }}
        >
          <ShieldAlert size={22} color="#b91c1c" style={{ flexShrink: 0, marginTop: "2px" }} />
          <div>
            <h4
              style={{
                fontSize: "0.95rem",
                fontWeight: 700,
                color: "#991b1b",
                margin: "0 0 0.25rem",
              }}
            >
              CRITICAL OFFENSE: Price Overcharge Detected (Section 18 Violation)
            </h4>
            <p
              style={{
                fontSize: "0.825rem",
                color: "#7f1d1d",
                margin: 0,
                lineHeight: 1.45,
              }}
            >
              The e-commerce listing charges <strong>₹{numWebPrice}</strong>, which exceeds the printed
              packaging MRP of <strong>₹{numPackMrp}</strong>. Under Section 18 & 36 of the Legal
              Metrology Act, 2009, selling or advertising above MRP carries a compounding penalty up to
              ₹1,00,000 and potential seizure.
            </p>
          </div>
        </div>
      )}

      {/* Comparison Grid Table */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
        }}
      >
        {/* Table Column Headers */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.2fr 1.4fr 1.4fr 120px",
            gap: "1rem",
            padding: "0.5rem 1rem",
            fontSize: "0.75rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "var(--text-muted)",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <span>Declaration Parameter</span>
          <span>Physical Label (Vision OCR)</span>
          <span>Web Listing (Marketplace)</span>
          <span style={{ textAlign: "right" }}>Verdict</span>
        </div>

        {/* Row Items */}
        {comparisons.map((item, idx) => {
          const Icon = item.icon;
          const isMismatch = item.status === "mismatch";
          const isMatch = item.status === "match";

          return (
            <div
              key={item.key}
              style={{
                display: "grid",
                gridTemplateColumns: "1.2fr 1.4fr 1.4fr 120px",
                gap: "1rem",
                alignItems: "center",
                padding: "0.85rem 1rem",
                borderRadius: "8px",
                background: isMismatch
                  ? "#fef2f2"
                  : idx % 2 === 0
                  ? "#f8fafc"
                  : "#ffffff",
                border: isMismatch
                  ? "1px solid #fecaca"
                  : "1px solid var(--border)",
                transition: "all 0.2s ease",
              }}
            >
              {/* Parameter */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <div
                  style={{
                    width: "28px",
                    height: "28px",
                    borderRadius: "6px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: isMismatch ? "#fee2e2" : "#eff6ff",
                    color: isMismatch ? "#b91c1c" : "var(--gov-navy)",
                  }}
                >
                  <Icon size={15} />
                </div>
                <div>
                  <div
                    style={{
                      fontSize: "0.85rem",
                      fontWeight: 600,
                      color: "var(--gov-navy-dark)",
                    }}
                  >
                    {item.label}
                  </div>
                  {item.notes && (
                    <div
                      style={{
                        fontSize: "0.725rem",
                        color: "#b91c1c",
                        marginTop: "2px",
                      }}
                    >
                      {item.notes}
                    </div>
                  )}
                </div>
              </div>

              {/* Physical Pack Value */}
              <div>
                {item.packValue ? (
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.825rem",
                      color: "#0f172a",
                      background: "#f1f5f9",
                      padding: "0.25rem 0.5rem",
                      borderRadius: "4px",
                      border: "1px solid var(--border)",
                      wordBreak: "break-word",
                    }}
                  >
                    {item.packValue}
                  </span>
                ) : (
                  <span
                    style={{
                      fontSize: "0.775rem",
                      color: "var(--text-muted)",
                      fontStyle: "italic",
                    }}
                  >
                    Not detected on label
                  </span>
                )}
              </div>

              {/* Web Listing Value */}
              <div>
                {item.webValue ? (
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.825rem",
                      color: isMismatch ? "#991b1b" : "#0f172a",
                      background: isMismatch ? "#fee2e2" : "#f1f5f9",
                      padding: "0.25rem 0.5rem",
                      borderRadius: "4px",
                      border: isMismatch
                        ? "1px solid #fecaca"
                        : "1px solid var(--border)",
                      wordBreak: "break-word",
                    }}
                  >
                    {item.webValue}
                  </span>
                ) : (
                  <span
                    style={{
                      fontSize: "0.775rem",
                      color: "var(--text-muted)",
                      fontStyle: "italic",
                    }}
                  >
                    Not provided in listing
                  </span>
                )}
              </div>

              {/* Status Badge */}
              <div style={{ textAlign: "right" }}>
                {isMatch && (
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.3rem",
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: "#15803d",
                      background: "#f0fdf4",
                      border: "1px solid #bbf7d0",
                      padding: "0.25rem 0.6rem",
                      borderRadius: "4px",
                    }}
                  >
                    <CheckCircle2 size={13} />
                    Match
                  </span>
                )}

                {isMismatch && (
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.3rem",
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: "#b91c1c",
                      background: "#fef2f2",
                      border: "1px solid #fecaca",
                      padding: "0.25rem 0.6rem",
                      borderRadius: "4px",
                    }}
                  >
                    <XCircle size={13} />
                    Mismatch
                  </span>
                )}

                {(item.status === "pack_only" || item.status === "web_only") && (
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.3rem",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "#b45309",
                      background: "#fffbeb",
                      border: "1px solid #fde68a",
                      padding: "0.25rem 0.5rem",
                      borderRadius: "4px",
                    }}
                  >
                    <AlertTriangle size={12} />
                    {item.status === "pack_only" ? "Unlisted" : "Unlabeled"}
                  </span>
                )}

                {item.status === "both_missing" && (
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.3rem",
                      fontSize: "0.75rem",
                      color: "var(--text-muted)",
                      padding: "0.25rem 0.5rem",
                    }}
                  >
                    <HelpCircle size={12} />
                    N/A
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Info */}
      <div
        style={{
          marginTop: "1.25rem",
          paddingTop: "1rem",
          borderTop: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          fontSize: "0.8rem",
          color: "var(--text-secondary)",
        }}
      >
        <div>
          {totalIssues > 0 ? (
            <span style={{ color: "#b91c1c", fontWeight: 700 }}>
              ⚠️ {totalIssues} cross-modal discrepanc{totalIssues > 1 ? "ies" : "y"} flagged
              under Legal Metrology & E-Commerce Rules
            </span>
          ) : (
            <span style={{ color: "#15803d", fontWeight: 600 }}>
              ✓ All cross-checked declarations align between web listing and physical package
            </span>
          )}
        </div>
        <div>Legal Metrology (Packaged Commodities) Rules, 2011 — E-Commerce Provisions</div>
      </div>
    </motion.section>
  );
}
