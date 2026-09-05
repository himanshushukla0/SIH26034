---
name: vision-label-ocr
description: >-
  Provides computer vision, image processing, and OCR workflows for detecting, cropping, de-skewing, and extracting text from product packaging and labels.
  Use when designing OCR pipelines, calculating font heights in millimeters, de-warping cylindrical packages, or extracting label bounding boxes.
---

# Computer Vision & OCR for Packaging Inspection

This skill guides the implementation of high-accuracy vision pipelines tailored for pre-packaged commodities and curved, reflective, or distorted packaging.

## Vision Pipeline Architecture

1. **Pre-processing & Enhancement:**
   - **Contrast & Illumination Normalization:** CLAHE (Contrast Limited Adaptive Histogram Equalization) to combat glare and shadows on plastic/foil wrappers.
   - **Bilateral Filtering:** Preserves sharp text edges while removing high-frequency packaging noise.
   - **Perspective Correction:** Four-point contour detection to rectify skewed box packages to orthographic top-down views.
   - **Cylindrical Unwarping:** For soda cans, spice jars, and plastic bottles, use polynomial cylinder mapping to unroll 3D curved text onto a flat plane before passing to OCR.

2. **Text Detection & Recognition (OCR):**
   - **Primary Engine:** PaddleOCR (PP-OCRv4) / EasyOCR / TrOCR for high accuracy on alphanumeric strings, multilingual packaging (Hindi, English, regional scripts).
   - **Multimodal LLM Verification:** Gemini 1.5/Flash Vision for zero-shot semantic extraction of structured fields directly from raw images.
   - **Spatial Key-Value Association:** Proximity-based bounding box graph matching: associating label keys (`MRP`, `Net Wt`, `Mfg Date`, `Customer Care`) with their adjacent values.

3. **Physical Font Height Measurement ($H_{mm}$):**
   - When a calibration marker (ArUco tag, coin, or known PDP dimension) is present:
     $$\text{PPI} = \frac{\text{Pixel Width of Reference}}{\text{Physical Width of Reference in Inches}}$$
     $$\text{Font Height (mm)} = \left(\frac{\text{Bounding Box Height in Pixels}}{\text{PPI}}\right) \times 25.4$$
   - Compare measured $H_{mm}$ against LMPC Rule 7 minimum thresholds.

4. **Contrast Ratio Compliance:**
   - Extract foreground font color $L_1$ and immediate background bounding zone $L_2$.
   - Calculate relative luminance contrast ratio:
     $$\text{CR} = \frac{L_1 + 0.05}{L_2 + 0.05}$$
   - LMPC requires prominent and readable text (recommended $\text{CR} \ge 4.5:1$ following WCAG/packaging readability standards).
