import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from PIL import Image

try:
    import pymupdf as fitz
except ImportError:
    import fitz

logger = logging.getLogger("anumati-ml.signature_detector")


class SignatureDetector:
    """
    Detects official institutional rubber seals and handwritten ink signatures
    using color channel segmentation and vector drawing analysis.
    """

    def __init__(self, min_signature_strokes: int = 15):
        self.min_signature_strokes = min_signature_strokes

    @staticmethod
    def _detect_ink_and_seals_in_image(img: Image.Image) -> Dict[str, Any]:
        """
        Inspects an RGB image for signature strokes and colored institutional stamps
        (blue, purple, and red ink).
        """
        rgb_img = img.convert("RGB")
        width, height = rgb_img.size
        total_pixels = width * height

        # Sample pixel coordinates to detect colored ink
        # Official institutional stamps and signatures are predominantly blue, purple, or red
        colored_ink_pixels = 0
        signature_like_pixels = 0

        # Subsample for speed (step of 4 pixels)
        step = 4
        sampled_total = 0

        for y in range(0, height, step):
            for x in range(0, width, step):
                sampled_total += 1
                r, g, b = rgb_img.getpixel((x, y))

                # Blue / Purple ink detection (B > R + 20 and B > G + 20)
                if b > r + 20 and b > g + 20 and b > 70:
                    colored_ink_pixels += 1

                # Red seal ink detection (R > G + 35 and R > B + 35)
                elif r > g + 35 and r > b + 35 and r > 90:
                    colored_ink_pixels += 1

                # Dark stroke pixels (handwritten ink)
                elif r < 60 and g < 60 and b < 60:
                    signature_like_pixels += 1

        colored_ratio = colored_ink_pixels / max(sampled_total, 1)

        # Detect seal if colored ink ratio exceeds minimum threshold
        stamp_detected = colored_ratio > 0.003
        stamp_confidence = min(0.95, round(colored_ratio * 100, 2)) if stamp_detected else 0.15

        return {
            "stamp_detected": stamp_detected,
            "stamp_confidence": stamp_confidence,
            "colored_ink_ratio": round(colored_ratio, 4),
        }

    def detect_signatures_in_pdf(
        self,
        pdf_source: Union[str, Path, bytes],
        max_pages_to_check: int = 5
    ) -> Dict[str, Any]:
        """
        Inspects a PDF document's pages for signatures and official seals.
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
            }

        total_pages = len(doc)
        pages_to_scan = min(total_pages, max_pages_to_check)
        
        has_signature = False
        has_stamp = False
        highest_confidence = 0.20
        detections: List[Dict[str, Any]] = []

        with doc:
            for page_idx in range(pages_to_scan):
                page = doc[page_idx]
                page_num = page_idx + 1

                # 1. Vector drawings & embedded raster signature blocks
                drawings_count = len(page.get_drawings())
                images_count = len(page.get_images())

                # 2. Check for signature keywords in page text
                page_text = page.get_text().lower()
                has_sign_keyword = any(
                    k in page_text for k in ["signature", "authorized signatory", "principal", "director", "seal"]
                )

                # 3. Image analysis for stamps
                pix = page.get_pixmap(dpi=150)
                pil_img = Image.open(io.BytesIO(pix.tobytes("png")))
                img_analysis = self._detect_ink_and_seals_in_image(pil_img)

                # Signature heuristic: vector clusters or raster blocks near signature keywords
                page_signature = (drawings_count > self.min_signature_strokes or images_count > 0) and has_sign_keyword
                page_stamp = img_analysis["stamp_detected"]

                if page_signature:
                    has_signature = True
                    highest_confidence = max(highest_confidence, 0.85)

                if page_stamp:
                    has_stamp = True
                    highest_confidence = max(highest_confidence, img_analysis["stamp_confidence"])

                detections.append({
                    "page_number": page_num,
                    "signature_detected": page_signature,
                    "stamp_detected": page_stamp,
                    "vector_drawings": drawings_count,
                    "embedded_images": images_count,
                    "contains_sign_keywords": has_sign_keyword,
                })

        overall_detected = has_signature or has_stamp
        if not overall_detected:
            highest_confidence = 0.25

        return {
            "signature_detected": has_signature,
            "stamp_detected": has_stamp,
            "overall_detected": overall_detected,
            "confidence": round(highest_confidence, 2),
            "pages_analyzed": pages_to_scan,
            "page_detections": detections,
            "status": "verified" if overall_detected else "unverified_or_missing",
        }