#!/usr/bin/env python3
"""
 LMPC COMPLIANCE ENGINE (SIH26034) — IMAGE GATE & BARCODE DECODER

 THE BUG THIS EXISTS TO KILL:
   A selfie was uploaded and the system returned "98% COMPLIANT — Tata Tea Gold 500g,
   MRP Rs 320.00, USP Rs 0.64/g, FONT_HEIGHT Compliant, 10/10 checks passed."
   Nothing in that output came from the image. The pipeline had no gate: whatever came
   back from the model (or from a demo fallback) was rendered as fact.

 THE RULE THIS MODULE ENFORCES:
   An image must EARN the right to be audited. If it does not plausibly show product
   packaging, the request is refused with a reason — it does not fall through to a demo
   product, and it does not produce a score.
"""

from __future__ import annotations
import logging, os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import zxingcpp
    _ZXING = True
except ImportError:
    _ZXING = False

log = logging.getLogger("lmpc.vision")

OK = "OK"
NOT_A_LABEL = "NOT_A_LABEL"
CONTAINS_PERSON = "CONTAINS_PERSON"
TOO_BLURRY = "TOO_BLURRY"
TOO_SMALL = "TOO_SMALL"
UNREADABLE_FILE = "UNREADABLE_FILE"

# Tune against your own evaluation set and record the numbers you used — a judge asking
# "why 60?" deserves a better answer than "it felt right".
MIN_EDGE_LENGTH_PX = 400
BLUR_LAPLACIAN_MIN = 60.0
MIN_TEXT_LINES = 4                # printed rows of similarly-sized glyphs
MIN_EDGE_DENSITY = 0.002          # below this the frame is featureless


@dataclass
class ImageAssessment:
    status: str
    reason: str
    signals: Dict[str, Any] = field(default_factory=dict)
    guidance: str = ""

    @property
    def usable(self) -> bool:
        return self.status == OK

    def as_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "usable": self.usable, "reason": self.reason,
                "guidance": self.guidance, "signals": self.signals}


def _load(image_path: str) -> Optional[np.ndarray]:
    if not os.path.exists(image_path):
        return None
    return cv2.imread(image_path, cv2.IMREAD_COLOR)


def blur_score(gray: np.ndarray) -> float:
    """Variance of the Laplacian. Low = out of focus = OCR will invent characters."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def text_line_analysis(gray: np.ndarray) -> Dict[str, int]:
    """
    Look for printed TEXT LINES, not just busy pixels.

    An earlier version of this counted raw MSER regions. That was useless: a photograph
    of a face produced 1157 "text-like" regions and sailed through the gate. Natural
    images are full of blob-shaped regions.

    What separates print from a photograph is ALIGNMENT — printed declarations sit in
    horizontal rows of glyphs with near-identical heights. So we cluster candidate glyphs
    by vertical centre and count rows containing several similarly-sized regions.
    """
    h, w = gray.shape[:2]
    scale = 1000.0 / max(h, w)
    if scale < 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        h, w = gray.shape[:2]

    glyphs: List[Tuple[int, int, int, int]] = []
    try:
        mser = cv2.MSER_create(delta=5, min_area=30, max_area=int(0.02 * h * w))
        regions, _ = mser.detectRegions(gray)
        for r in regions:
            x, y, rw, rh = cv2.boundingRect(r.reshape(-1, 1, 2))
            if rh == 0 or rw == 0:
                continue
            aspect = rw / float(rh)
            fill = len(r) / float(rw * rh)
            if 0.1 <= aspect <= 3.0 and 0.15 <= fill <= 0.9 and 8 <= rh <= h * 0.15:
                glyphs.append((x, y, rw, rh))
    except (cv2.error, Exception):
        pass

    # Robust fallback if MSER returned few regions (e.g. OpenCV 5.x / thin fonts)
    if len(glyphs) < 15:
        try:
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
            )
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                x, y, rw, rh = cv2.boundingRect(c)
                if rh == 0 or rw == 0:
                    continue
                aspect = rw / float(rh)
                if 0.1 <= aspect <= 3.5 and 8 <= rh <= h * 0.15:
                    glyphs.append((x, y, rw, rh))
        except Exception:
            pass

    rows: Dict[int, List[Tuple[int, int, int, int]]] = {}
    for (x, y, rw, rh) in glyphs:
        band = int((y + rh / 2.0) // max(6, rh // 2 or 6))
        rows.setdefault(band, []).append((x, y, rw, rh))

    text_lines = regions_in_lines = 0
    for band, members in rows.items():
        if len(members) < 4:
            continue
        heights = [m[3] for m in members]
        median_h = sorted(heights)[len(heights) // 2]
        if median_h <= 0:
            continue
        consistent = [m for m in members if abs(m[3] - median_h) <= 0.45 * median_h]
        if len(consistent) < 4:
            continue
        xs = sorted(m[0] for m in consistent)
        if xs[-1] - xs[0] < 3 * median_h:      # must actually span horizontally
            continue
        text_lines += 1
        regions_in_lines += len(consistent)

    return {"regions": len(glyphs), "text_lines": text_lines,
            "regions_in_lines": regions_in_lines}


def edge_density(gray: np.ndarray) -> float:
    """Fraction of pixels on a Canny edge. Near zero means a featureless frame."""
    edges = cv2.Canny(gray, 50, 150)
    return float(np.count_nonzero(edges)) / float(edges.size)


def detect_faces(gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Haar cascade. Offline, no model download, ships with OpenCV."""
    faces: List[Tuple[int, int, int, int]] = []
    if not hasattr(cv2, "CascadeClassifier"):
        return faces
    for name in ("haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml"):
        candidates = []
        if hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            candidates.append(os.path.join(cv2.data.haarcascades, name))
        candidates.append(os.path.join(os.path.dirname(__file__), "backend", "data", "haarcascades", name))
        candidates.append(os.path.join(os.path.dirname(__file__), "data", "haarcascades", name))
        for path in candidates:
            if os.path.exists(path):
                try:
                    cascade = cv2.CascadeClassifier(path)
                    if not cascade.empty():
                        for (x, y, w, h) in cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60)):
                            faces.append((int(x), int(y), int(w), int(h)))
                        if faces:
                            return faces
                except Exception as e:
                    log.warning("Cascade detection error: %s", e)
    return faces


def skin_fraction(bgr: np.ndarray) -> float:
    """Secondary signal only — never used alone, since packaging can be beige."""
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, np.array([0, 133, 77], np.uint8),
                       np.array([255, 173, 127], np.uint8))
    return float(np.count_nonzero(mask)) / float(mask.size)


def assess_image(image_path: str) -> ImageAssessment:
    """
    Decide whether this image may be audited at all. Ordering is deliberate: cheap
    structural failures first, so the officer gets the most actionable message.
    """
    img = _load(image_path)
    if img is None:
        return ImageAssessment(UNREADABLE_FILE,
            "The uploaded file could not be read as an image.",
            guidance="Upload a JPEG or PNG photograph of the package.")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    signals: Dict[str, Any] = {"width": w, "height": h}

    if min(h, w) < MIN_EDGE_LENGTH_PX:
        signals["min_edge_px"] = min(h, w)
        return ImageAssessment(TOO_SMALL,
            f"Image is {w}x{h}. The short edge must be at least {MIN_EDGE_LENGTH_PX}px "
            f"for declaration text to be legible.", signals,
            guidance="Retake the photograph closer to the package, or at a higher resolution.")

    density = edge_density(gray)
    signals["edge_density"] = round(density, 5)
    if density < MIN_EDGE_DENSITY:
        return ImageAssessment(NOT_A_LABEL,
            "No legible printed content could be found in this image. It is either badly "
            "out of focus or does not show a package label. No audit has been performed "
            "and no verdict has been recorded.", signals,
            guidance=("Photograph the declaration panel of the package so it fills the "
                      "frame, and tap to focus before taking the shot."))

    blur = blur_score(gray)
    signals["blur_laplacian_variance"] = round(blur, 1)
    if blur < BLUR_LAPLACIAN_MIN:
        return ImageAssessment(TOO_BLURRY,
            f"Image is out of focus (sharpness {blur:.0f}, minimum {BLUR_LAPLACIAN_MIN:.0f}). "
            f"Text extracted from a blurred label cannot be relied on.", signals,
            guidance="Hold the camera steady, tap to focus on the declaration panel, retake.")

    barcodes = decode_barcodes(image_path)
    signals["barcodes_found"] = len(barcodes)

    text = text_line_analysis(gray)
    signals.update(text)

    faces = detect_faces(gray)
    signals["faces_detected"] = len(faces)
    if faces:
        largest = max(fw * fh for (_, _, fw, fh) in faces)
        signals["largest_face_area_fraction"] = round(largest / float(w * h), 4)
        signals["skin_fraction"] = round(skin_fraction(img), 4)

        # ANY detected human face with no barcode stops the audit. There is no safe
        # threshold here: the cost of auditing a person is a fabricated legal verdict,
        # and the cost of refusing a real package is one retake.
        if not barcodes:
            return ImageAssessment(CONTAINS_PERSON,
                "This photograph appears to show a person, not a pre-packaged commodity. "
                "No compliance audit has been performed and no verdict has been recorded.",
                signals,
                guidance=("Photograph the Principal Display Panel of the package — the face "
                          "of the pack carrying the MRP, net quantity and manufacturer "
                          "details. If this really is a package that pictures a person, "
                          "include the barcode in the frame."))

    if text["text_lines"] < MIN_TEXT_LINES and not barcodes:
        return ImageAssessment(NOT_A_LABEL,
            f"No barcode was found and no printed declaration text could be located "
            f"({text['text_lines']} text lines detected, minimum {MIN_TEXT_LINES}). "
            f"No audit has been performed.", signals,
            guidance=("Photograph the side or back panel of the package where the "
                      "mandatory declarations are printed, filling the frame."))

    return ImageAssessment(OK, "Image accepted for label extraction.", signals,
        guidance="" if barcodes else
                 ("No barcode is visible in this image. Declarations will be read from the "
                  "label only; product identity cannot be cross-checked against a "
                  "reference database."))


@dataclass
class DecodedBarcode:
    text: str
    format: str
    valid_checksum: Optional[bool] = None
    position: Optional[Dict[str, int]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "format": self.format,
                "valid_checksum": self.valid_checksum, "position": self.position}


def decode_barcodes(image_path: str) -> List[DecodedBarcode]:
    """
    Decode every barcode in the image. Tries as-is, upscaled, rotated, greyscaled — a
    pack photographed on a shelf is rarely axis-aligned, and a single failed read used to
    be the thing that pushed the old pipeline down its demo-fallback path.
    """
    if not _ZXING:
        log.warning("zxing-cpp not installed; barcode decoding disabled")
        return []
    img = _load(image_path)
    if img is None:
        return []

    attempts = [img]
    h, w = img.shape[:2]
    if max(h, w) < 1600:
        attempts.append(cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC))
    attempts.append(cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE))
    attempts.append(cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR))

    seen: Dict[str, DecodedBarcode] = {}
    for candidate in attempts:
        try:
            results = zxingcpp.read_barcodes(candidate)
        except Exception as exc:
            log.warning("barcode decode attempt failed: %s", exc)
            continue
        for r in results:
            text = (r.text or "").strip()
            if not text or text in seen:
                continue
            pos = None
            try:
                p = r.position
                pos = {"x": int(p.top_left.x), "y": int(p.top_left.y)}
            except Exception:
                pass
            seen[text] = DecodedBarcode(text=text, format=str(r.format), position=pos,
                                        valid_checksum=_gtin_checksum_ok(text))
        if seen:
            break
    return list(seen.values())


def _gtin_checksum_ok(text: str) -> Optional[bool]:
    digits = "".join(c for c in text if c.isdigit())
    if len(digits) not in (8, 12, 13, 14) or len(digits) != len(text):
        return None
    body, check = digits[:-1], int(digits[-1])
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


NO_BARCODE = "NO_BARCODE_DETECTED"
BARCODE_UNREADABLE = "BARCODE_PRESENT_BUT_UNREADABLE"
BARCODE_OK = "BARCODE_DECODED"


def barcode_status(image_path: str) -> Dict[str, Any]:
    """
    Resolve the barcode situation into something the UI can state plainly.

    A missing barcode is NOT an error and NOT a compliance failure — Rule 6 does not
    require a barcode at all. It only means product identity cannot be cross-checked.
    The audit continues on the label text alone, at reduced confidence.
    """
    codes = decode_barcodes(image_path)

    if codes:
        primary = codes[0]
        note = ""
        if primary.valid_checksum is False:
            note = (" The check digit does not validate, so this is not a well-formed "
                    "GTIN — record it but treat the identity as unconfirmed.")
        return {"status": BARCODE_OK, "barcode": primary.text, "format": primary.format,
                "valid_checksum": primary.valid_checksum,
                "all_barcodes": [c.as_dict() for c in codes],
                "message": f"Barcode decoded: {primary.text} ({primary.format}).{note}",
                "blocks_audit": False,
                "confidence_penalty": 0.0 if primary.valid_checksum else 0.1}

    if _has_barcode_like_pattern(image_path):
        return {"status": BARCODE_UNREADABLE, "barcode": None,
                "message": ("A barcode appears to be present but could not be decoded — "
                            "most often glare, motion blur, a curved surface, or the code "
                            "running off the edge of the frame."),
                "guidance": ("Retake the barcode straight on, without flash glare, with the "
                             "whole code inside the frame. You can also key the digits in "
                             "manually from beneath the bars."),
                "blocks_audit": False, "confidence_penalty": 0.15}

    return {"status": NO_BARCODE, "barcode": None,
            "message": ("No barcode detected in this image. This is not a compliance "
                        "failure — Rule 6 does not require a barcode. It means the "
                        "product's identity cannot be cross-checked against a reference "
                        "database, so the declarations below are read from the label alone."),
            "guidance": ("If the pack carries a barcode, photograph it to enable identity "
                         "cross-checking. Otherwise enter the product name manually so the "
                         "audit record can be attributed."),
            "blocks_audit": False, "confidence_penalty": 0.2}


def _has_barcode_like_pattern(image_path: str) -> bool:
    """
    Cheap detector for a 1-D barcode: a dense band of near-vertical high-contrast edges.
    Used only to distinguish "no barcode here" from "there is a barcode and I failed to
    read it" — a distinction that changes the officer's next action.
    """
    img = _load(image_path)
    if img is None:
        return False
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (min(1200, gray.shape[1]), min(900, gray.shape[0])))

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.convertScaleAbs(cv2.subtract(np.absolute(gx), np.absolute(gy)))

    _, thresh = cv2.threshold(cv2.blur(grad, (9, 9)), 200, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    closed = cv2.dilate(cv2.erode(closed, None, iterations=4), None, iterations=4)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w * h < 2000 or h == 0:
            continue
        if 1.5 <= w / float(h) <= 12.0:
            return True
    return False


def prepare_audit_input(image_path: str) -> Dict[str, Any]:
    """
    THE ONE FUNCTION YOUR API SHOULD CALL.

    If `proceed` is False, the caller MUST return the refusal to the user and MUST NOT
    call the vision model, MUST NOT write an audit row, and MUST NOT emit a score.
    """
    assessment = assess_image(image_path)

    if not assessment.usable:
        return {"proceed": False, "image": assessment.as_dict(), "barcode": None,
                "audit_status": "REFUSED", "user_message": assessment.reason,
                "guidance": assessment.guidance}

    bc = barcode_status(image_path)
    return {"proceed": True, "image": assessment.as_dict(), "barcode": bc,
            "audit_status": "READY", "user_message": bc["message"],
            "guidance": bc.get("guidance", "") or assessment.guidance,
            "base_confidence": round(max(0.0, 1.0 - bc["confidence_penalty"]), 2)}
