/**
 * SIH26034 — API Client
 *
 * TypeScript client for communicating with the LMPC Compliance
 * Engine FastAPI backend.
 */

import { FALLBACK_ANALYTICS, getFallbackAuditResult } from "./utils/demoData";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/** Extracted declaration field with confidence. */
export interface ExtractionField {
  value: string | number | boolean | null;
  confidence: number;
}

/** Full extractions from the Vision Agent. */
export interface PackagingExtractions {
  product_name?: ExtractionField;
  manufacturer_name?: ExtractionField;
  manufacturer_address?: ExtractionField;
  country_of_origin?: ExtractionField;
  generic_name?: ExtractionField;
  net_quantity?: ExtractionField;
  net_quantity_unit?: ExtractionField;
  net_quantity_value?: ExtractionField;
  manufacture_date?: ExtractionField;
  expiry_date?: ExtractionField;
  best_before?: ExtractionField;
  mrp?: ExtractionField;
  mrp_includes_taxes?: ExtractionField;
  unit_sale_price?: ExtractionField;
  consumer_care_name?: ExtractionField;
  consumer_care_phone?: ExtractionField;
  consumer_care_email?: ExtractionField;
  consumer_care_address?: ExtractionField;
  barcode_number?: ExtractionField;
  is_imported?: ExtractionField;
  importer_name?: ExtractionField;
  importer_address?: ExtractionField;
  additional_declarations?: string[];
  detected_languages?: string[];
  packaging_type?: string;
  label_readability?: string;
  [key: string]: unknown;
}

/** Single violation record with Ministry of Consumer Affairs statutory citations. */
export interface Violation {
  rule_reference: string;
  act_section?: string;
  punishment_section?: string;
  statutory_penalty?: string;
  legal_proof_summary?: string;
  field_name: string;
  severity: "critical" | "major" | "minor";
  description: string;
  expected_value: string | null;
  found_value: string | null;
  is_discrepancy: boolean;
}

/** Declaration status for a single field. */
export interface DeclarationStatus {
  status: "FOUND" | "MISSING" | "PARTIAL";
  value?: string;
  [key: string]: unknown;
}

/** Complete audit verdict backed by Ministry of Consumer Affairs statutes. */
export interface AuditVerdict {
  compliance_score: number;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  overall_status: "COMPLIANT" | "NON_COMPLIANT" | "PARTIAL_VIOLATION" | "NEEDS_MANUAL_REVIEW";
  computed_usp: string | null;
  declaration_status: Record<string, DeclarationStatus>;
  violations: Violation[];
  statutory_authority?: string;
  governing_act?: string;
  governing_rules?: string;
  corporate_liability_clause?: string;
  manual_review_reasons?: string[];
}

/** Single verification check result from the authenticity scanner. */
export interface VerificationCheck {
  check_name: string;
  status: "VERIFIED" | "FAILED" | "WARNING" | "UNVERIFIABLE";
  confidence: number;
  details: string;
  evidence: Record<string, unknown>;
  is_counterfeit_signal: boolean;
}

/** Package authenticity verdict from the verification agent. */
export interface PackageAuthenticityVerdict {
  trust_score: number;
  overall_status: "AUTHENTIC" | "SUSPICIOUS" | "COUNTERFEIT_RISK";
  counterfeit_signals: number;
  expiry_status: "VALID" | "EXPIRED" | "NEAR_EXPIRY" | "DATE_TAMPERED" | "UNKNOWN";
  days_until_expiry: number | null;
  checks: VerificationCheck[];
}

/** Full audit response from the backend. */
export interface AuditResponse {
  input_type: "image" | "url" | "camera";
  source_url?: string;
  platform?: string;
  stage: string;
  error: string | null;
  listing_data?: Record<string, unknown>;
  extractions: PackagingExtractions;
  verdict: AuditVerdict | null;
  verification?: PackageAuthenticityVerdict | null;
  audit_id?: string;
  report_url?: string;
  status?: string;
  audit_status?: string;
  reason?: string;
  guidance?: string;
  image_assessment?: Record<string, unknown>;
}

/** Health check response. */
export interface HealthResponse {
  status: string;
  service: string;
  model: string;
  version: string;
}

/** Barcode verification response. */
export interface BarcodeVerificationResponse {
  barcode: string;
  barcode_identity: {
    status: string;
    details: string;
    evidence: Record<string, unknown>;
    is_counterfeit_signal: boolean;
  };
  gs1_country: {
    status: string;
    details: string;
    evidence: Record<string, unknown>;
  };
}

/** FSSAI verification response. */
export interface FssaiVerificationResponse {
  license_number: string;
  status: string;
  details: string;
  evidence: Record<string, unknown>;
  is_counterfeit_signal: boolean;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

/** Check if the backend server is healthy. */
export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

/** Submit a packaging image for LMPC compliance audit. */
export async function auditImage(file: File): Promise<AuditResponse> {
  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/api/audit/image`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      // Preserve statutory Image Gate refusals (HTTP 422 or explicit refusal)
      if (res.status === 422 || err.status === "REFUSED" || err.audit_status === "REFUSED") {
        return {
          input_type: "image",
          stage: "completed",
          status: "REFUSED",
          audit_status: "REFUSED",
          error: err.detail || err.error || "Image refused by statutory Image Gate.",
          reason: err.detail || err.reason || "The image does not show pre-packaged commodity declarations.",
          guidance: err.guidance || "Photograph the declaration panel of the package and tap to focus.",
          image_assessment: err.image_assessment || err.image,
          extractions: {},
          verdict: null,
        };
      }
      throw new Error(err.detail || `Audit failed: ${res.status}`);
    }

    const data = await res.json();
    if (data.status === "REFUSED" || data.audit_status === "REFUSED") {
      return {
        input_type: "image",
        stage: "completed",
        status: "REFUSED",
        audit_status: "REFUSED",
        error: data.error || data.reason || data.detail,
        reason: data.reason || data.detail || "The image does not show pre-packaged commodity declarations.",
        guidance: data.guidance || "Photograph the declaration panel of the package and tap to focus.",
        image_assessment: data.image_assessment || data.image,
        extractions: {},
        verdict: null,
      };
    }
    return data;
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    if (errMsg.includes("Image refused") || errMsg.includes("not show") || errMsg.includes("REFUSED")) {
      return {
        input_type: "image",
        stage: "completed",
        status: "REFUSED",
        audit_status: "REFUSED",
        error: errMsg,
        reason: errMsg,
        guidance: "Photograph the declaration panel of the package and tap to focus.",
        extractions: {},
        verdict: null,
      };
    }
    console.warn("Cloud backend unreachable, running statutory client simulation:", err);
    return getFallbackAuditResult("image", file.name);
  }
}

/** Submit an e-commerce URL for LMPC compliance audit. */
export async function auditUrl(url: string): Promise<AuditResponse> {
  try {
    const formData = new FormData();
    formData.append("url", url);

    const res = await fetch(`${API_BASE}/api/audit/url`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `URL audit failed: ${res.status}`);
    }

    return await res.json();
  } catch (err) {
    console.warn("Cloud backend unreachable, running statutory client simulation:", err);
    return getFallbackAuditResult("url", url);
  }
}

/** Submit a camera scan with optional pre-decoded barcode. */
export async function scanPackage(
  imageBlob: Blob,
  barcode?: string,
): Promise<AuditResponse> {
  try {
    const formData = new FormData();
    formData.append("file", imageBlob, "scan.jpg");
    if (barcode) {
      formData.append("barcode", barcode);
    }

    const res = await fetch(`${API_BASE}/api/scan`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      // Preserve statutory Image Gate refusals (HTTP 422 or explicit refusal)
      if (res.status === 422 || err.status === "REFUSED" || err.audit_status === "REFUSED") {
        return {
          input_type: "camera",
          stage: "completed",
          status: "REFUSED",
          audit_status: "REFUSED",
          error: err.detail || err.error || "Frame refused by statutory Image Gate.",
          reason: err.detail || err.reason || "The frame does not show pre-packaged commodity declarations.",
          guidance: err.guidance || "Align the packaging Principal Display Panel or barcode in the camera frame.",
          image_assessment: err.image_assessment || err.image,
          extractions: {},
          verdict: null,
        };
      }
      throw new Error(err.detail || `Scan failed: ${res.status}`);
    }

    const data = await res.json();
    if (data.status === "REFUSED" || data.audit_status === "REFUSED") {
      return {
        input_type: "camera",
        stage: "completed",
        status: "REFUSED",
        audit_status: "REFUSED",
        error: data.error || data.reason || data.detail,
        reason: data.reason || data.detail || "The frame does not show pre-packaged commodity declarations.",
        guidance: data.guidance || "Align the packaging Principal Display Panel or barcode in the camera frame.",
        image_assessment: data.image_assessment || data.image,
        extractions: {},
        verdict: null,
      };
    }
    return data;
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    if (errMsg.includes("refused") || errMsg.includes("not show") || errMsg.includes("REFUSED")) {
      return {
        input_type: "camera",
        stage: "completed",
        status: "REFUSED",
        audit_status: "REFUSED",
        error: errMsg,
        reason: errMsg,
        guidance: "Align the packaging Principal Display Panel or barcode in the camera frame.",
        extractions: {},
        verdict: null,
      };
    }
    console.warn("Cloud backend unreachable, running statutory client simulation:", err);
    return getFallbackAuditResult("camera", barcode || "");
  }
}

/** Standalone barcode verification. */
export async function verifyBarcode(
  barcode: string,
): Promise<BarcodeVerificationResponse> {
  const res = await fetch(`${API_BASE}/api/verify/barcode/${encodeURIComponent(barcode)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Verification failed: ${res.status}`);
  }
  return res.json();
}

/** Standalone FSSAI license verification. */
export async function verifyFssai(
  licenseNumber: string,
): Promise<FssaiVerificationResponse> {
  const res = await fetch(`${API_BASE}/api/verify/fssai/${encodeURIComponent(licenseNumber)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `FSSAI verification failed: ${res.status}`);
  }
  return res.json();
}

export interface TopFieldStat {
  field: string;
  count: number;
}

export interface TopContraventionStat {
  contravention: string;
  count: number;
}

export interface TopBrandStat {
  brand: string;
  violations_count: number;
}

export interface RecentAuditStat {
  id: string;
  created_at: string | null;
  product_name: string;
  manufacturer: string;
  compliance_score: number;
  overall_status: string;
  violations_count: number;
}

export interface AnalyticsSummary {
  total_audits: number;
  compliant_count: number;
  non_compliant_count: number;
  manual_review_count: number;
  compliance_rate: number;
  average_compliance_score: number;
  total_violations: number;
  violations_by_severity: {
    critical: number;
    major: number;
    minor: number;
  };
  top_violated_fields: TopFieldStat[];
  top_contraventions: TopContraventionStat[];
  top_offending_brands: TopBrandStat[];
  estimated_fines_inr: number;
  recent_audits: RecentAuditStat[];
}

/** Retrieve aggregate analytics for Legal Metrology officers. */
export async function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/summary`);
    if (!res.ok) {
      throw new Error(`Failed to fetch analytics: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn("Backend unavailable, loading cached enforcement intelligence:", err);
    return FALLBACK_ANALYTICS;
  }
}

export interface StatutoryNoticeResult {
  instrument: "IMPROVEMENT_NOTICE" | "SHOW_CAUSE" | "NONE";
  text: string;
  reason: string;
  ref?: string;
  audit_id?: string;
}

export interface DraftNoticeRequest {
  item: {
    name?: string;
    manufacturer?: string;
    barcode?: string;
    data_source?: string;
    checks?: string[];
  };
  failures: Array<{
    rule_id: string;
    found?: string;
    detail?: string;
  }>;
  officer_name?: string;
  ref?: string;
  offence_number?: number;
  compliance_days?: number;
}

/** Generate an official statutory Improvement Notice (s.15(6)) or Show Cause Notice. */
export async function draftStatutoryNotice(req: DraftNoticeRequest): Promise<StatutoryNoticeResult> {
  try {
    const res = await fetch(`${API_BASE}/api/notice/draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to draft notice: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn("Backend unavailable, generating client statutory notice:", err);
    const isFirst = (req.offence_number || 1) === 1;
    const instrument = req.failures.length === 0 ? "NONE" : (isFirst ? "IMPROVEMENT_NOTICE" : "SHOW_CAUSE");
    const ref = req.ref || `LMPC/HQ/2026/${Math.floor(100000 + Math.random() * 900000)}`;
    const dateStr = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });

    if (instrument === "NONE") {
      return {
        instrument: "NONE",
        text: "",
        reason: "No contravention was recorded, so no notice arises.",
        ref,
      };
    }

    if (instrument === "IMPROVEMENT_NOTICE") {
      const text = [
        "======================================================================================",
        "*** D R A F T  —  N O T   I S S U E D ***",
        "IMPROVEMENT NOTICE UNDER SECTION 15(6), LEGAL METROLOGY ACT, 2009",
        "======================================================================================",
        "",
        "PROTOTYPE OUTPUT — generated by a decision-support tool built for Smart India Hackathon PS SIH26034.",
        "--------------------------------------------------------------------------------------",
        `Draft reference : ${ref}`,
        `Prepared on     : ${dateStr}`,
        `Prepared by     : ${req.officer_name || "Inspector of Legal Metrology, Enforcement Division"}`,
        `Rule table      : 2026.09-janvishwas2026`,
        "",
        "To,",
        `M/s ${req.item.manufacturer || "(manufacturer / packer / importer to be identified)"}`,
        "",
        `Commodity       : ${req.item.name || "-"}`,
        `Barcode / GTIN  : ${req.item.barcode || "-"}`,
        `Evidence basis  : ${req.item.data_source || "Multi-Agent Vision & OCR Inspection"}`,
        "",
        "WHEREAS on inspection of the above pre-packaged commodity there are grounds to believe",
        "that the requirements of section 18 of the Legal Metrology Act, 2009 read with Rule 6",
        "of the Legal Metrology (Packaged Commodities) Rules, 2011 have not been complied with;",
        "",
        "(a) GROUNDS AND (b) MATTERS CONSTITUTING THE FAILURE:",
        ...req.failures.map((f, i) => `  [${i + 1}] Rule ${f.rule_id}: Observed '${f.found || f.detail || "-"}'`),
        "",
        "(c) MEASURES REQUIRED TO SECURE COMPLIANCE:",
        ...req.failures.map((_, i) => `  [${i + 1}] Rectify labelling to conform with Legal Metrology (Packaged Commodities) Rules, 2011.`),
        "",
        `(d) PERIOD FOR COMPLIANCE: you are required to take the measures specified above within ${req.compliance_days || 30} days of service of this notice.`,
        "",
        "CONSEQUENCE OF NON-COMPLIANCE: under section 15(7) of the Act, failure to comply with an improvement notice may result in suspension or revocation of your registration, after a hearing. Subsequent contravention attracts civil penalties under Section 36(1).",
        "",
        "APPEAL: an appeal against this notice lies under section 50 of the Act within 60 days.",
        "======================================================================================",
      ].join("\n");

      return {
        instrument: "IMPROVEMENT_NOTICE",
        text,
        reason: "Every recorded contravention is a first contravention of a provision for which section 15(6) prescribes a warning with an improvement notice (Jan Vishwas 2026).",
        ref,
      };
    }

    const text = [
      "======================================================================================",
      "*** D R A F T  —  N O T   I S S U E D ***",
      "SHOW CAUSE NOTICE — LEGAL METROLOGY ACT, 2009",
      "======================================================================================",
      `Draft reference : ${ref}`,
      `Prepared on     : ${dateStr}`,
      `Prepared by     : ${req.officer_name || "Inspector of Legal Metrology"}`,
      `Recorded as contravention number ${req.offence_number || 2} for this addressee.`,
      "",
      `To M/s ${req.item.manufacturer || "Responsible Entity"}`,
      "",
      "NOW THEREFORE you are called upon to show cause in writing within 15 days as to why action should not be taken.",
      "======================================================================================",
    ].join("\n");

    return {
      instrument: "SHOW_CAUSE",
      text,
      reason: `Recorded as contravention number ${req.offence_number || 2}, which is past the improvement-notice stage.`,
      ref,
    };
  }
}

