export type Language = "en" | "hi";

export interface TranslationDictionary {
  // Top bar
  topbar_sih_title: string;
  topbar_proposal: string;
  topbar_helpline: string;
  // Masthead
  masthead_dept: string;
  masthead_title: string;
  masthead_prototype_badge: string;
  masthead_proposal_sub: string;
  auditor_cockpit: string;
  sih_sandbox: string;
  ai_active: string;
  ai_offline: string;
  // Tabs
  tab_livescan: string;
  tab_scanner: string;
  tab_url: string;
  tab_analytics: string;
  // Demo shelf
  demo_shelf_label: string;
  demo_tata_tea: string;
  demo_garam_masala: string;
  demo_choco_wafers: string;
  demo_honey: string;
  // Offline banner
  low_conn_mode: string;
  online_sync_active: string;
  inspections_queued: string;
  sync_to_db: string;
  syncing: string;
  // Hero 1 - Live Scan
  livescan_badge: string;
  livescan_title: string;
  livescan_desc: string;
  telemetry_vision: string;
  telemetry_fssai: string;
  telemetry_registry: string;
  telemetry_penalties: string;
  // Hero 2 - Image Upload
  upload_badge: string;
  upload_title: string;
  upload_desc: string;
  telemetry_10_decl: string;
  telemetry_usp_math: string;
  telemetry_s36: string;
  // Hero 3 - URL Auditor
  url_badge: string;
  url_title: string;
  url_desc: string;
  // LiveScanner Component
  camera_field: string;
  camera_ready: string;
  camera_live: string;
  align_barcode_reticle: string;
  camera_support_desc: string;
  activate_camera: string;
  scan_another: string;
  deactivate_camera: string;
  capture_frame_btn: string;
  upload_scan_image: string;
  switch_camera: string;
  scanning_active_hud: string;
  manual_search_title: string;
  manual_search_sub: string;
  manual_placeholder: string;
  verify_button: string;
  evaluating_commodity: string;
  // Audit Report
  statutory_audit_banner: string;
  act_reference_subtitle: string;
  statutory_enforcement_sub: string;
  print_notice_btn: string;
  verdict_score_label: string;
  mandatory_checked_label: string;
  violations_found_label: string;
  status_compliant: string;
  status_non_compliant: string;
  status_partial: string;
  status_manual_review: string;
  severity_critical: string;
  severity_major: string;
  severity_minor: string;
  computed_usp_label: string;
  declarations_checklist_title: string;
  violations_section_title: string;
  export_pdf_btn: string;
  // Footer
  footer_prototype_title: string;
  footer_desc: string;
  badge_gigw: string;
  badge_multiagent: string;
  footer_portals_title: string;
  footer_acts_title: string;
  footer_copy_left: string;
  footer_copy_right: string;
}

export type TranslationKey = keyof TranslationDictionary;

export const translations: Record<Language, TranslationDictionary> = {
  en: {
    topbar_sih_title: "Smart India Hackathon | SIH26034 Innovation Prototype",
    topbar_proposal: "Proposal for Department of Consumer Affairs",
    topbar_helpline: "National Consumer Helpline: 1915",
    masthead_dept: "विधिक मापविज्ञान (पैकेज्ड कमोडिटीज) अनुपालन प्रणाली",
    masthead_title: "AUTOMATED LMPC COMPLIANCE ENGINE",
    masthead_prototype_badge: "SIH26034 PROTOTYPE",
    masthead_proposal_sub: "Proposed AI Solution for Department of Consumer Affairs",
    auditor_cockpit: "Auditor Cockpit View",
    sih_sandbox: "SIH Live Demonstration Sandbox",
    ai_active: "GEMINI 3.6 FLASH • ACTIVE",
    ai_offline: "OFFLINE CACHE",
    tab_livescan: "Field Camera Scanner",
    tab_scanner: "Evidence Image Upload",
    tab_url: "E-Commerce URL Auditor",
    tab_analytics: "Officer MIS & Seizures",
    demo_shelf_label: "Quick Field Demonstrations:",
    demo_tata_tea: "🍵 Tata Tea Gold 500g (100% Compliant)",
    demo_garam_masala: "🌶️ Royal Shahi Garam Masala (Statutory Infractions)",
    demo_choco_wafers: "🍫 Swiss Choco Crunch Wafers (Imported / Missing Origin)",
    demo_honey: "🍯 Himalayan Multi-Floral Honey (Compliant)",
    low_conn_mode: "📡 Low Connectivity Field Mode",
    online_sync_active: "🌐 Online Sync Active",
    inspections_queued: "inspection(s) queued in local encrypted storage",
    sync_to_db: "Sync to National DB",
    syncing: "Syncing...",
    livescan_badge: "LEGAL METROLOGY ACT, 2009 • SECTION 15 STATUTORY ENFORCEMENT",
    livescan_title: "Real-Time Packaging Authenticity & Statutory Scanner",
    livescan_desc:
      "Point device camera at any pre-packaged commodity. Multi-agent OCR decodes barcodes, verifies FSSAI 14-digit licenses, inspects expiry integrity, and cross-checks mandatory Rule 6 declarations.",
    telemetry_vision: "Vision: Gemini 3.6 Flash Multimodal",
    telemetry_fssai: "FSSAI: 14-Digit FoSCoS Validator",
    telemetry_registry: "Registry: GS1 India DataKart Lookup",
    telemetry_penalties: "Penalties: Section 36 & Section 29",
    upload_badge: "RULE 6(1) STATUTORY AUDITOR • MULTIMODAL OCR",
    upload_title: "Statutory Packaging Label Inspection",
    upload_desc:
      "Capture or upload packaging labels during market inspections. Multi-agent OCR audits all mandatory declarations, checks Unit Sale Price (USP) math, and generates court-ready statutory notices.",
    telemetry_10_decl: "Mandatory: 10 Declarations",
    telemetry_usp_math: "Unit Price: Rule 6(11) Math",
    telemetry_s36: "Penalties: Section 36 Ready",
    url_badge: "E-COMMERCE DISCREPANCY AUDITOR • RULE 6(10) ENFORCEMENT",
    url_title: "E-Commerce Market Listing Auditor",
    url_desc:
      "Cross-verify digital marketplace product pages against physical packaging disclosures across Amazon, Blinkit, Zepto, Flipkart, and Instamart. Detect deceptive MRP markup and missing origin.",
    camera_field: "FIELD INSPECTION CAMERA",
    camera_ready: "CAMERA READY",
    camera_live: "LIVE STREAM ACTIVE",
    align_barcode_reticle: "Align Barcode / QR Inside Reticle",
    camera_support_desc:
      "Supports Indian EAN-13, GS1 DataBar, FSSAI 14-digit codes, and imported commodity labels.",
    activate_camera: "Activate Inspection Camera",
    scan_another: "Scan Another Package",
    deactivate_camera: "Deactivate Camera",
    capture_frame_btn: "Capture Frame & Audit Label",
    upload_scan_image: "Or Upload Barcode / Packaging Photo",
    switch_camera: "Switch Camera",
    scanning_active_hud: "Optical Barcode Detection Active",
    manual_search_title: "🔍 Manual Code or License Verification",
    manual_search_sub: "GTIN-13 / EAN / FSSAI (14-digit)",
    manual_placeholder: "Enter Barcode or 14-digit FSSAI number (e.g. 8901030383478)...",
    verify_button: "Verify Commodity",
    evaluating_commodity: "Evaluating Commodity Statutory Compliance...",
    statutory_audit_banner:
      "Statutory Legal Metrology Compliance Audit • The Legal Metrology Act, 2009 (Act No. 1 of 2010)",
    act_reference_subtitle:
      "⚖️ Statutory Legal Metrology Compliance Audit • Department of Consumer Affairs Guidelines (SIH26034)",
    statutory_enforcement_sub:
      "Enforced under Sections 11, 15, 18, 29, 36 & 49 of the Act read with Legal Metrology (Packaged Commodities) Rules, 2011",
    print_notice_btn: "Print Statutory Notice",
    verdict_score_label: "Overall Score",
    mandatory_checked_label: "Mandatory Declarations Checked",
    violations_found_label: "Violations Detected",
    status_compliant: "COMPLIANT",
    status_non_compliant: "NON-COMPLIANT",
    status_partial: "PARTIAL VIOLATION",
    status_manual_review: "MANUAL REVIEW REQUIRED",
    severity_critical: "CRITICAL",
    severity_major: "MAJOR",
    severity_minor: "MINOR",
    computed_usp_label: "Computed USP:",
    declarations_checklist_title: "Statutory Declarations Verification (Rule 6)",
    violations_section_title: "Detected Violations & Non-Compliances",
    export_pdf_btn: "Export Audit Dossier (PDF)",
    footer_prototype_title: "Smart India Hackathon (SIH26034) Prototype",
    footer_desc:
      "An automated, multi-agent AI verification prototype designed to audit mandatory packaging declarations under the Legal Metrology (Packaged Commodities) Rules, 2011 and the Legal Metrology Act, 2009. Built as a technical proposal for the Department of Consumer Affairs.",
    badge_gigw: "GIGW 3.0 UX Standards",
    badge_multiagent: "Multi-Agent AI",
    footer_portals_title: "Statutory Reference Portals",
    footer_acts_title: "Statutory Acts & Enforcements",
    footer_copy_left:
      "🇮🇳 Smart India Hackathon (SIH26034) Innovation Project • Proposed to Department of Consumer Affairs",
    footer_copy_right:
      "Demonstration & Evaluation Sandbox • Designed with GovTech UI/UX Principles",
  },
  hi: {
    topbar_sih_title: "स्मार्ट इंडिया हैकाथॉन | SIH26034 नवाचार प्रोटोटाइप",
    topbar_proposal: "उपभोक्ता मामले विभाग हेतु प्रस्तावित समाधान",
    topbar_helpline: "राष्ट्रीय उपभोक्ता हेल्पलाइन: 1915",
    masthead_dept: "विधिक मापविज्ञान (पैकेज्ड कमोडिटीज) अनुपालन प्रणाली",
    masthead_title: "स्वचालित एलएमपीसी अनुपालन इंजन",
    masthead_prototype_badge: "SIH26034 प्रोटोटाइप",
    masthead_proposal_sub: "उपभोक्ता मामले विभाग हेतु प्रस्तावित एआई समाधान",
    auditor_cockpit: "लेखापरीक्षक कॉकपिट दृश्य",
    sih_sandbox: "SIH लाइव प्रदर्शन सैंडबॉक्स",
    ai_active: "जेमिनी 3.6 फ़्लैश • सक्रिय",
    ai_offline: "ऑफ़लाइन कैश",
    tab_livescan: "फील्ड कैमरा स्कैनर",
    tab_scanner: "साक्ष्य छवि अपलोड",
    tab_url: "ई-कॉमर्स यूआरएल ऑडिटर",
    tab_analytics: "अधिकारी एमआईएस और ज़ब्ती डेटा",
    demo_shelf_label: "त्वरित फील्ड प्रदर्शन:",
    demo_tata_tea: "🍵 टाटा टी गोल्ड 500g (100% अनुपालन)",
    demo_garam_masala: "🌶️ रॉयल शाही गरम मसाला (वैधानिक उल्लंघन)",
    demo_choco_wafers: "🍫 स्विस चोको क्रंच वेफर्स (आयातित / मूल देश अनुपस्थित)",
    demo_honey: "🍯 हिमालयन मल्टी-फ्लोरल हनी (अनुपालन)",
    low_conn_mode: "📡 कम कनेक्टिविटी फील्ड मोड",
    online_sync_active: "🌐 ऑनलाइन सिंक सक्रिय",
    inspections_queued: "स्थानीय एन्क्रिप्टेड स्टोरेज में निरीक्षण कतारबद्ध",
    sync_to_db: "राष्ट्रीय डेटाबेस में सिंक करें",
    syncing: "सिंक हो रहा है...",
    livescan_badge: "विधिक मापविज्ञान अधिनियम, 2009 • धारा 15 वैधानिक प्रवर्तन",
    livescan_title: "वास्तविक समय पैकेजिंग प्रामाणिकता एवं वैधानिक स्कैनर",
    livescan_desc:
      "डिवाइस कैमरा को किसी भी पूर्व-पैकेज्ड वस्तु पर लक्षित करें। मल्टी-एजेंट ओसीआर बारकोड डिकोड करता है, 14-अंकीय FSSAI लाइसेंस सत्यापित करता है और नियम 6 घोषणाओं की जांच करता है।",
    telemetry_vision: "विजन: जेमिनी 3.6 फ़्लैश मल्टीमॉडल",
    telemetry_fssai: "FSSAI: 14-अंकीय FoSCoS सत्यापनकर्ता",
    telemetry_registry: "रजिस्ट्री: GS1 इंडिया डेटाकार्ट लुकअप",
    telemetry_penalties: "दंड: धारा 36 एवं धारा 29",
    upload_badge: "नियम 6(1) वैधानिक लेखापरीक्षा • मल्टीमॉडल ओसीआर",
    upload_title: "वैधानिक पैकेजिंग लेबल निरीक्षण",
    upload_desc:
      "बाजार निरीक्षण के दौरान पैकेजिंग लेबल अपलोड करें। मल्टी-एजेंट ओसीआर सभी अनिवार्य घोषणाओं की जांच करता है, प्रति इकाई मूल्य (USP) की गणना करता है और कोर्ट-रेडी नोटिस तैयार करता है।",
    telemetry_10_decl: "अनिवार्य: 10 वैधानिक घोषणाएं",
    telemetry_usp_math: "इकाई मूल्य: नियम 6(11) गणित",
    telemetry_s36: "दंड: धारा 36 तैयार",
    url_badge: "ई-कॉमर्स विसंगति परीक्षक • नियम 6(10) प्रवर्तन",
    url_title: "ई-कॉमर्स मार्केट लिस्टिंग ऑडिटर",
    url_desc:
      "अमेज़न, ब्लिंकिट, ज़ेप्टो, फ्लिपकार्ट और इंस्टामार्ट पर डिजिटल उत्पाद पृष्ठों का पैकेजिंग लेबल के साथ मिलान करें। भ्रामक एमआरपी और गुम देश का तुरंत पता लगाएं।",
    camera_field: "फील्ड निरीक्षण कैमरा",
    camera_ready: "कैमरा तैयार",
    camera_live: "लाइव स्ट्रीम सक्रिय",
    align_barcode_reticle: "रेटिकल के अंदर बारकोड / क्यूआर संरेखित करें",
    camera_support_desc:
      "भारतीय EAN-13, GS1 डेटाबार, FSSAI 14-अंकीय कोड और आयातित पैकेजिंग लेबल का समर्थन करता है।",
    activate_camera: "निरीक्षण कैमरा सक्रिय करें",
    scan_another: "अन्य पैकेज स्कैन करें",
    deactivate_camera: "कैमरा बंद करें",
    capture_frame_btn: "फ्रेम कैप्चर करें एवं लेबल जांचें",
    upload_scan_image: "अथवा बारकोड / पैकेजिंग फोटो अपलोड करें",
    switch_camera: "कैमरा बदलें",
    scanning_active_hud: "ऑप्टिकल बारकोड पहचान सक्रिय",
    manual_search_title: "🔍 मैनुअल कोड अथवा लाइसेंस सत्यापन",
    manual_search_sub: "GTIN-13 / EAN / FSSAI (14-अंकीय)",
    manual_placeholder: "बारकोड या 14-अंकीय FSSAI नंबर दर्ज करें (उदा. 8901030383478)...",
    verify_button: "वस्तु सत्यापित करें",
    evaluating_commodity: "वस्तु के वैधानिक अनुपालन का मूल्यांकन किया जा रहा है...",
    statutory_audit_banner:
      "वैधानिक विधिक मापविज्ञान अनुपालन ऑडिट • विधिक मापविज्ञान अधिनियम, 2009 (अधिनियम सं. 1/2010)",
    act_reference_subtitle:
      "⚖️ वैधानिक विधिक मापविज्ञान अनुपालन ऑडिट • उपभोक्ता मामले विभाग दिशानिर्देश (SIH26034)",
    statutory_enforcement_sub:
      "विधिक मापविज्ञान (पैकेज्ड कमोडिटीज) नियम 2011 के साथ पठित अधिनियम की धारा 11, 15, 18, 29, 36 और 49 के तहत प्रवर्तित",
    print_notice_btn: "वैधानिक नोटिस प्रिंट करें",
    verdict_score_label: "कुल अनुपालन स्कोर",
    mandatory_checked_label: "जांची गई अनिवार्य घोषणाएं",
    violations_found_label: "पाए गए वैधानिक उल्लंघन",
    status_compliant: "पूर्णतः अनुपालन (COMPLIANT)",
    status_non_compliant: "गैर-अनुपालन (NON-COMPLIANT)",
    status_partial: "आंशिक उल्लंघन (PARTIAL VIOLATION)",
    status_manual_review: "मैनुअल समीक्षा आवश्यक (MANUAL REVIEW)",
    severity_critical: "गंभीर",
    severity_major: "प्रमुख",
    severity_minor: "गौण",
    computed_usp_label: "गणना किया गया प्रति इकाई मूल्य (USP):",
    declarations_checklist_title: "वैधानिक घोषणा सत्यापन (नियम 6)",
    violations_section_title: "पाए गए उल्लंघन एवं कमियां",
    export_pdf_btn: "ऑडिट डोजियर निर्यात करें (PDF)",
    footer_prototype_title: "स्मार्ट इंडिया हैकाथॉन (SIH26034) प्रोटोटाइप",
    footer_desc:
      "विधिक मापविज्ञान अधिनियम, 2009 एवं विधिक मापविज्ञान (पैकेज्ड कमोडिटीज) नियम, 2011 के तहत अनिवार्य पैकेजिंग घोषणाओं की लेखापरीक्षा के लिए विकसित स्वचालित मल्टी-एजेंट एआई प्रोटोटाइप। उपभोक्ता मामले विभाग हेतु तकनीकी प्रस्ताव।",
    badge_gigw: "GIGW 3.0 यूएक्स मानक",
    badge_multiagent: "मल्टी-एजेंट एआई",
    footer_portals_title: "वैधानिक संदर्भ पोर्टल",
    footer_acts_title: "वैधानिक अधिनियम और प्रवर्तन",
    footer_copy_left:
      "🇮🇳 स्मार्ट इंडिया हैकाथॉन (SIH26034) नवाचार परियोजना • उपभोक्ता मामले विभाग हेतु प्रस्तावित",
    footer_copy_right:
      "प्रदर्शन और मूल्यांकन सैंडबॉक्स • GovTech UI/UX सिद्धांतों के अनुरूप तैयार",
  },
};
