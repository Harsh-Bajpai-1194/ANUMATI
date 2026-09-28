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
    using color channel segmentation, spatial vector proximity, and OCR fallback.
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
        signature_ratio = signature_like_pixels / max(sampled_total, 1)

        # Detect seal if colored ink ratio exceeds minimum threshold
        stamp_detected = colored_ratio > 0.003
        stamp_confidence = min(0.95, round(colored_ratio * 100, 2)) if stamp_detected else 0.15

        return {
            "stamp_detected": stamp_detected,
            "stamp_confidence": stamp_confidence,
            "colored_ink_ratio": round(colored_ratio, 4),
            "signature_ratio": round(signature_ratio, 4),
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
        
        # Scan first few pages and the last page (where signatures commonly appear)
        pages_to_scan_indices = list(range(min(total_pages, max_pages_to_check)))
        if total_pages > max_pages_to_check and (total_pages - 1) not in pages_to_scan_indices:
            pages_to_scan_indices.append(total_pages - 1)
            
        has_signature = False
        has_stamp = False
        highest_confidence = 0.20
        detections: List[Dict[str, Any]] = []

        with doc:
            for page_idx in pages_to_scan_indices:
                page = doc[page_idx]
                page_num = page_idx + 1

                # 1. Vector drawings & embedded raster signature blocks
                drawings_count = len(page.get_drawings())
                images_count = len(page.get_images())

                # 2. Image analysis for stamps and ink
                pix = page.get_pixmap(dpi=150)
                pil_img = Image.open(io.BytesIO(pix.tobytes("png")))
                img_analysis = self._detect_ink_and_seals_in_image(pil_img)

                # 3. Extract text with OCR fallback for scanned PDFs
                page_text = page.get_text().lower()
                if not page_text.strip():
                    try:
                        import pytesseract
                        page_text = pytesseract.image_to_string(pil_img).lower()
                    except Exception:
                        pass
                
                kw_list = ["signature", "authorized signatory", "principal", "director", "seal"]
                has_sign_keyword = any(k in page_text for k in kw_list)

                # 4. Spatial correlation: Check if drawings are physically near keywords
                signature_near_keyword = False
                if has_sign_keyword and drawings_count > self.min_signature_strokes:
                    keyword_rects = []
                    for kw in ["signature", "authorized", "signatory", "principal", "director"]:
                        keyword_rects.extend(page.search_for(kw))
                    
                    for path in page.get_drawings():
                        path_rect = path.get("rect")
                        if path_rect:
                            for kw_rect in keyword_rects:
                                # Check if drawing is within ~150 points vertically of keyword
                                if abs(path_rect.y1 - kw_rect.y1) < 150:
                                    signature_near_keyword = True
                                    break
                        if signature_near_keyword:
                            break

                # Signature heuristic: 
                # A. Vector drawings spatially located near a signature keyword
                # B. OR High concentration of handwritten-like dark pixels (fallback for images)
                page_signature = signature_near_keyword or (img_analysis.get("signature_ratio", 0.0) > 0.015)
                
                # Require corroborating evidence (keywords or drawings) for stamps to prevent false positives from blue headers
                page_stamp = img_analysis["stamp_detected"] and (has_sign_keyword or drawings_count > 0)

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
            "pages_analyzed": len(pages_to_scan_indices),  # Fixed NameError here
            "page_detections": detections,
            "status": "verified" if has_signature else "unverified_or_missing",
        }
    