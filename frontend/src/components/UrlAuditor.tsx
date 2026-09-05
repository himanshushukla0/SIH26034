import { useState } from "react";
import { motion } from "framer-motion";
import { Globe, Search, ArrowRight } from "lucide-react";

interface UrlAuditorProps {
  onSubmit: (url: string) => void;
  isLoading: boolean;
}

const PLATFORM_EXAMPLES = [
  { name: "Amazon India", url: "https://www.amazon.in/dp/B00N1Y86W4", color: "#ea580c" },
  { name: "Blinkit", url: "https://blinkit.com/prn/tata-tea-gold-500g/prid/12345", color: "#ca8a04" },
  { name: "Zepto", url: "https://www.zeptonow.com/pn/amul-butter-pasteurised-500-g/p/98765", color: "#7c3aed" },
  { name: "Flipkart", url: "https://www.flipkart.com/imported-choco-crunch-wafers/p/itm12345", color: "#2563eb" },
  { name: "Swiggy Instamart", url: "https://www.swiggy.com/instamart/item/cadbury-dairy-milk-silk-150g", color: "#ea580c" },
];

export default function UrlAuditor({ onSubmit, isLoading }: UrlAuditorProps) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!url.trim()) {
      setError("Please enter a product listing URL.");
      return;
    }

    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      setError("URL must start with http:// or https://");
      return;
    }

    onSubmit(url.trim());
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{ maxWidth: "800px", margin: "0 auto" }}
    >
      <div className="gov-card" style={{ padding: "2rem" }}>
        <div style={{ marginBottom: "1.5rem", textAlign: "center" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "8px",
              background: "var(--gov-navy-light)",
              border: "1px solid #bfdbfe",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 0.75rem",
            }}
          >
            <Globe size={24} color="#0b3b60" />
          </div>
          <h3
            style={{
              fontSize: "1.15rem",
              fontWeight: 700,
              color: "var(--gov-navy-dark)",
              marginBottom: "0.35rem",
            }}
          >
            E-Commerce Mandatory Disclosures Auditor (Rule 6(10) Compliance)
          </h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", maxWidth: "560px", margin: "0 auto", lineHeight: 1.5 }}>
            Paste a product listing URL from any Indian e-commerce marketplace.
            The multi-agent pipeline extracts digital disclosures and verifies compliance with
            the Legal Metrology (Packaged Commodities) Rules, 2011.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <div style={{ position: "relative", flex: 1 }}>
              <Search
                size={18}
                style={{
                  position: "absolute",
                  left: "14px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--gov-navy-primary)",
                  pointerEvents: "none",
                }}
              />
              <input
                type="url"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setError("");
                }}
                placeholder="Paste Amazon, Flipkart, Blinkit, Zepto, or Instamart URL..."
                disabled={isLoading}
                id="url-input-field"
                style={{
                  width: "100%",
                  paddingLeft: "42px",
                  paddingRight: "12px",
                  height: "48px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.9rem",
                  border: "1px solid var(--border-card)",
                  background: "#ffffff",
                  outline: "none",
                }}
              />
            </div>
            <button
              type="submit"
              className="btn-gov-primary"
              disabled={isLoading || !url.trim()}
              id="url-audit-submit"
              style={{
                height: "48px",
                padding: "0 1.5rem",
              }}
            >
              {isLoading ? (
                <>Auditing...</>
              ) : (
                <>
                  Inspect Listing
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>

          {error && (
            <p
              style={{
                color: "var(--gov-red)",
                fontSize: "0.82rem",
                marginTop: "0.5rem",
                textAlign: "left",
                fontWeight: 600,
              }}
            >
              {error}
            </p>
          )}
        </form>

        {/* Quick Demo URLs */}
        <div
          style={{
            marginTop: "1.5rem",
            paddingTop: "1.25rem",
            borderTop: "1px solid var(--border-card)",
          }}
        >
          <div
            style={{
              fontSize: "0.75rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              marginBottom: "0.5rem",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            📋 Quick-Test E-Commerce Marketplaces (Click to Paste):
          </div>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "0.5rem",
            }}
          >
            {PLATFORM_EXAMPLES.map((p) => (
              <button
                key={p.name}
                onClick={() => setUrl(p.url)}
                type="button"
                className="btn-gov-secondary"
                style={{
                  padding: "0.35rem 0.75rem",
                  fontSize: "0.75rem",
                }}
              >
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: p.color,
                  }}
                />
                <span>{p.name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
