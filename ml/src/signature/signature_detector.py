import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from PIL import Image, ImageDraw
import numpy as np

try:
    import pymupdf as fitz
except ImportError:
    import fitz

logger = logging.getLogger("anumati-ml.signature_detector")

SIGNATURE_KEYWORDS = [
    "authorized signatory",
    "authorised signatory",
    "signature",
    "signatory",
    "principal",
    "director",
    "head of institute",
    "head of institution",
]


class SignatureDetector:
    """
    Detects official institutional rubber seals and candidate handwritten ink signatures
    using keyword-anchored spatial ROI analysis, text masking, and color channel segmentation.
    
    Status outputs:
      - 'signature_candidate': Indication of ink or vector strokes in a signature zone (routes to human review).
      - 'not_found': No candidate signature strokes identified near signature keywords.
    """

    def __init__(self, min_signature_strokes: int = 5, min_ink_pixels: int = 40):
        self.min_signature_strokes = min_signature_strokes
        self.min_ink_pixels = min_ink_pixels

    @staticmethod
    def _detect_ink_and_seals_in_image(img: Image.Image) -> Dict[str, Any]:
        """
        Inspects an RGB image for colored institutional stamps
        (blue, purple, and red ink) using fast NumPy vectorized color segmentation.
        """
        rgb_img = img.convert("RGB")
        arr = np.array(rgb_img)
        r = arr[:, :, 0].astype(np.int16)
        g = arr[:, :, 1].astype(np.int16)
        b = arr[:, :, 2].astype(np.int16)

        # Blue / Purple ink detection: (B > R + 20 and B > G + 20 and B > 70)
        blue_purple_mask = (b > r + 20) & (b > g + 20) & (b > 70)

        # Red seal ink detection: (R > G + 35 and R > B + 35 and R > 90)
        red_mask = (r > g + 35) & (r > b + 35) & (r > 90)

        colored_mask = blue_purple_mask | red_mask
        colored_ink_pixels = int(np.count_nonzero(colored_mask))
        total_pixels = max(arr.shape[0] * arr.shape[1], 1)
        colored_ratio = colored_ink_pixels / total_pixels

        # Detect seal if colored ink ratio exceeds minimum calibrated threshold (0.3% of page)
        stamp_detected = colored_ratio > 0.003
        stamp_confidence = min(0.95, round(colored_ratio * 100, 2)) if stamp_detected else 0.15

        return {
            "stamp_detected": stamp_detected,
            "stamp_confidence": stamp_confidence,
            "colored_ink_ratio": round(colored_ratio, 4),
        }

    def _check_signature_in_keyword_roi(
        self,
        page: fitz.Page,
        kw_rect: fitz.Rect,
        dpi: int = 150
    ) -> tuple[bool, float]:
        """
        Inspects a bounded region near a signature keyword.
        Masks out all known printed text boxes to avoid false positives on dense text,
        then evaluates residual vector drawings and dark/colored pen strokes.
        """
        page_rect = page.rect
        # Anchor ROI above and around the keyword (typical signing area: 20-110 pts above)
        roi_rect = fitz.Rect(
            max(0, kw_rect.x0 - 40),
            max(0, kw_rect.y0 - 110),
            min(page_rect.width, kw_rect.x1 + 80),
            min(page_rect.height, kw_rect.y1 + 10)
        )

        if roi_rect.is_empty or roi_rect.width <= 0 or roi_rect.height <= 0:
            return False, 0.0

        # 1. Vector strokes in ROI
        drawings_in_roi = 0
        for draw in page.get_drawings():
            draw_rect = draw.get("rect")
            if draw_rect and draw_rect.intersects(roi_rect):
                drawings_in_roi += 1

        if drawings_in_roi >= self.min_signature_strokes:
            return True, 0.85

        # 2. Raster ink in ROI with known text boxes masked out
        scale = dpi / 72.0
        pix = page.get_pixmap(clip=roi_rect, dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        draw_tool = ImageDraw.Draw(img)

        # Mask out all digital words intersecting the ROI
        words = page.get_text("words")
        for w in words:
            w_rect = fitz.Rect(w[0], w[1], w[2], w[3])
            if w_rect.intersects(roi_rect):
                px0 = max(0, int((w_rect.x0 - roi_rect.x0) * scale) - 2)
                py0 = max(0, int((w_rect.y0 - roi_rect.y0) * scale) - 2)
                px1 = min(img.width, int((w_rect.x1 - roi_rect.x0) * scale) + 2)
                py1 = min(img.height, int((w_rect.y1 - roi_rect.y0) * scale) + 2)
                draw_tool.rectangle([px0, py0, px1, py1], fill=(255, 255, 255))

        # Check for residual ink pixels that do not belong to printed text
        arr = np.array(img)
        r = arr[:, :, 0].astype(np.int16)
        g = arr[:, :, 1].astype(np.int16)
        b = arr[:, :, 2].astype(np.int16)

        # Dark pen ink (black/dark grey)
        dark_ink = (r < 100) & (g < 100) & (b < 100)
        # Blue / purple pen ink
        blue_purple_ink = (b > r + 15) & (b > g + 15) & (b > 60)
        # Red pen ink
        red_ink = (r > g + 30) & (r > b + 30) & (r > 80)

        residual_ink_mask = dark_ink | blue_purple_ink | red_ink
        residual_ink_count = int(np.count_nonzero(residual_ink_mask))
        total_roi_pixels = max(arr.shape[0] * arr.shape[1], 1)
        residual_ratio = residual_ink_count / total_roi_pixels

        # Require minimum pixel count and ratio of unmasked ink
        if residual_ink_count >= self.min_ink_pixels and residual_ratio >= 0.003:
            return True, 0.80

        return False, 0.20

    def detect_signatures_in_pdf(
        self,
        pdf_source: Union[str, Path, bytes],
        max_pages_to_check: int = 5
    ) -> Dict[str, Any]:
        """
        Inspects a PDF document's pages for candidate signatures and official seals.
        Returns status 'signature_candidate' or 'not_found' for human-in-the-loop review.
        """
        try:
            if isinstance(pdf_source, (str, Path)):
                doc = fitz.open(pdf_source)
            else:
                doc = fitz.open(stream=pdf_source, filetype="pdf")
        except Exception as exc:
            logger.error(f"Failed to open PDF for signature detection: {exc}")
            return {
                "signature_detected": False,
                "stamp_detected": False,
                "confidence": 0.0,
                "error": str(exc),
                "status": "not_found",
            }

        total_pages = len(doc)
        pages_to_scan_indices = list(range(min(total_pages, max_pages_to_check)))
        if total_pages > max_pages_to_check and (total_pages - 1) not in pages_to_scan_indices:
            pages_to_scan_indices.append(total_pages - 1)

        has_signature_candidate = False
        has_stamp = False
        highest_confidence = 0.20
        detections: List[Dict[str, Any]] = []

        with doc:
            for page_idx in pages_to_scan_indices:
                page = doc[page_idx]
                page_num = page_idx + 1

                # 1. Fast vectorized stamp detection
                pix = page.get_pixmap(dpi=150)
                pil_img = Image.open(io.BytesIO(pix.tobytes("png")))
                img_analysis = self._detect_ink_and_seals_in_image(pil_img)

                # 2. Search for signature keywords on page
                keyword_rects = []
                for kw in SIGNATURE_KEYWORDS:
                    matches = page.search_for(kw)
                    if matches:
                        keyword_rects.extend(matches)

                # OCR fallback for keyword detection on scanned pages without text layer
                if not keyword_rects and not page.get_text().strip():
                    try:
                        import pytesseract
                        ocr_data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
                        scale = 72.0 / 150.0  # Pixels to PDF points
                        for i, word in enumerate(ocr_data.get("text", [])):
                            clean_word = word.strip().lower()
                            if any(kw in clean_word for kw in ["sign", "signature", "signatory", "director", "principal"]):
                                left = ocr_data["left"][i] * scale
                                top = ocr_data["top"][i] * scale
                                width = ocr_data["width"][i] * scale
                                height = ocr_data["height"][i] * scale
                                keyword_rects.append(fitz.Rect(left, top, left + width, top + height))
                    except Exception:
                        pass

                has_sign_keyword = len(keyword_rects) > 0

                # 3. Check for signatures strictly inside the ROI near keywords
                page_signature_candidate = False
                for kw_rect in keyword_rects:
                    is_cand, conf = self._check_signature_in_keyword_roi(page, kw_rect)
                    if is_cand:
                        page_signature_candidate = True
                        highest_confidence = max(highest_confidence, conf)
                        break

                # 4. Stamp detection corroborated by keyword or drawings
                drawings_count = len(page.get_drawings())
                page_stamp = img_analysis["stamp_detected"] and (has_sign_keyword or drawings_count > 0)
                if page_stamp:
                    has_stamp = True
                    highest_confidence = max(highest_confidence, img_analysis["stamp_confidence"])

                if page_signature_candidate:
                    has_signature_candidate = True

                detections.append({
                    "page_number": page_num,
                    "signature_detected": page_signature_candidate,
                    "stamp_detected": page_stamp,
                    "vector_drawings": drawings_count,
                    "contains_sign_keywords": has_sign_keyword,
                })

        overall_detected = has_signature_candidate or has_stamp
        if not overall_detected:
            highest_confidence = 0.20

        status = "signature_candidate" if has_signature_candidate else "not_found"

        return {
            "signature_detected": has_signature_candidate,
            "stamp_detected": has_stamp,
            "overall_detected": overall_detected,
            "confidence": round(highest_confidence, 2),
            "pages_analyzed": len(pages_to_scan_indices),
            "page_detections": detections,
            "status": status,
        }
    