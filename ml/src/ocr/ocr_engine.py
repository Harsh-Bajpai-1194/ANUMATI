import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from PIL import Image

from src.config import TEXT_FOLDER
from src.preprocessing.pdf_reader import PDFReader, PDFProcessingError
from .image_preprocessor import ImagePreprocessor

logger = logging.getLogger("anumati-ml.ocr_engine")

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    PYTESSERACT_AVAILABLE = False


class OCREngineError(Exception):
    pass


class OCREngine:
    def __init__(
        self,
        min_words_threshold: int = 15,
        dpi: int = 300,
        preprocessor: Optional[ImagePreprocessor] = None,
        apply_binarization: bool = False,
    ):
        self.min_words_threshold = min_words_threshold
        self.dpi = dpi
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.apply_binarization = apply_binarization

    def _run_tesseract(self, img: Image.Image) -> tuple[str, float]:
        if not PYTESSERACT_AVAILABLE or pytesseract is None:
            logger.warning("pytesseract is not installed; scanned page OCR fallback is skipped.")
            return "", 0.0

        try:
            processed_img = self.preprocessor.preprocess(
                img,
                apply_binarization=self.apply_binarization
            )
            # Fetch actual word confidences
            data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) != -1]
            
            text = pytesseract.image_to_string(processed_img)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            
            return text.strip(), (avg_conf / 100.0)
        except Exception as exc:
            logger.warning(f"Tesseract OCR execution failed: {exc}")
            return "", 0.0

    def process_document(
        self,
        reader_or_source: Union[PDFReader, str, Path, bytes, io.BytesIO],
        document_name: Optional[str] = None,
        save_text_file: bool = True
    ) -> Dict[str, Any]:
        if isinstance(reader_or_source, PDFReader):
            reader = reader_or_source
        elif isinstance(reader_or_source, (str, Path, bytes, io.BytesIO)):
            reader = PDFReader(reader_or_source, document_name=document_name)
        else:
            raise OCREngineError(f"Unsupported reader or source type: {type(reader_or_source)}")

        doc_stem = reader.document_stem
        total_pages = reader.total_pages()
        pages_result: List[Dict[str, Any]] = []
        total_words = 0
        total_chars = 0
        used_digital = False
        used_ocr = False

        try:
            with reader.open_pdf() as pdf:
                for page_idx in range(total_pages):
                    page = pdf[page_idx]
                    page_number = page_idx + 1

                    digital_text = page.get_text().strip()
                    words = len(digital_text.split())
                    final_page_text = digital_text
                    method = "digital_text_layer"
                    ocr_conf = None

                    if words < self.min_words_threshold:
                        ocr_text = ""
                        try:
                            pix = page.get_pixmap(dpi=self.dpi)
                            img = Image.open(io.BytesIO(pix.tobytes("png")))
                            ocr_text, ocr_conf = self._run_tesseract(img)
                        except Exception as exc:
                            logger.warning(
                                f"OCR pipeline failed on page {page_number} of '{reader.document_name}': {exc}"
                            )

                        if ocr_text:
                            ocr_words = len(ocr_text.split())
                            if ocr_words > words:
                                if digital_text and digital_text not in ocr_text:
                                    final_page_text = f"{digital_text}\n\n{ocr_text}".strip()
                                else:
                                    final_page_text = ocr_text
                                words = len(final_page_text.split())
                                method = "ocr_fallback"
                                used_ocr = True
                            else:
                                final_page_text = digital_text
                                method = "digital_text_layer" if words > 0 else "empty_or_unreadable"
                                if words > 0:
                                    used_digital = True
                        else:
                            if words > 0:
                                method = "digital_text_layer"
                                used_digital = True
                            else:
                                method = "empty_or_unreadable"
                    else:
                        used_digital = True

                    chars = len(final_page_text)
                    total_words += words
                    total_chars += chars

                    pages_result.append({
                        "page_number": page_number,
                        "word_count": words,
                        "char_count": chars,
                        "method": method,
                        "text": final_page_text,
                        "digital_text": digital_text,
                        "ocr_confidence": ocr_conf if method == "ocr_fallback" else None
                    })
        except Exception as exc:
            if not isinstance(exc, OCREngineError):
                raise OCREngineError(f"Document OCR extraction interrupted: {exc}") from exc
            raise

        if used_digital and used_ocr:
            overall_method = "hybrid"
        elif used_ocr:
            overall_method = "ocr_fallback"
        elif used_digital:
            overall_method = "digital_text_layer"
        else:
            overall_method = "unreadable_or_empty"

        valid_confs = [p["ocr_confidence"] for p in pages_result if p.get("ocr_confidence") is not None]
        mean_ocr_conf = sum(valid_confs) / len(valid_confs) if valid_confs else None

        full_text = "\n\n".join([p["text"] for p in pages_result if p["text"]])

        text_file_path = None
        if save_text_file:
            import uuid
            text_file_path = TEXT_FOLDER / doc_stem / uuid.uuid4().hex / "extracted_text.txt"
            text_file_path.parent.mkdir(parents=True, exist_ok=True)
            text_file_path.write_text(full_text, encoding="utf-8")
            logger.info(f"Saved extracted text to: {text_file_path}")

        return {
            "document_name": reader.document_name,
            "total_pages": total_pages,
            "total_words": total_words,
            "total_characters": total_chars,
            "extraction_method": overall_method,
            "ocr_engine_available": PYTESSERACT_AVAILABLE,
            "ocr_confidence": mean_ocr_conf,
            "text_file_path": str(text_file_path) if text_file_path else None,
            "pages": pages_result,
            "full_text": full_text,
        }
    