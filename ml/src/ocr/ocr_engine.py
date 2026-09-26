import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from src.config import TEXT_FOLDER
from src.preprocessing.pdf_reader import PDFReader
from .image_preprocessor import ImagePreprocessor

logger = logging.getLogger("anumati-ml.ocr_engine")

# Check if pytesseract is available in environment
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


class OCREngineError(Exception):
    """Exception raised for errors during OCR and text extraction."""
    pass


class OCREngine:
    """
    Hybrid Document Text Extraction Engine.
    Combines direct digital layer extraction with optical character recognition (OCR)
    for scanned or low-density pages.
    """

    def __init__(
        self,
        min_words_threshold: int = 15,
        dpi: int = 300,
        preprocessor: Optional[ImagePreprocessor] = None
    ):
        """
        Parameters:
            min_words_threshold (int): Minimum words required to consider a page a digital PDF.
                                      Pages with fewer words trigger OCR image processing.
            dpi (int): DPI resolution for page rendering if OCR fallback is needed.
            preprocessor (Optional[ImagePreprocessor]): Preprocessor instance for OCR images.
        """
        self.min_words_threshold = min_words_threshold
        self.dpi = dpi
        self.preprocessor = preprocessor or ImagePreprocessor()

    def _run_tesseract(self, image_path: Path) -> str:
        """Runs Tesseract OCR if available, else returns empty string."""
        if not PYTESSERACT_AVAILABLE:
            logger.warning(
                "pytesseract is not installed; scanned page OCR fallback is skipped."
            )
            return ""

        try:
            processed_img = self.preprocessor.preprocess(image_path)
            text = pytesseract.image_to_string(processed_img)
            return text.strip()
        except Exception as exc:
            logger.warning(f"Tesseract OCR failed on {image_path}: {exc}")
            return ""

    def process_document(
        self,
        reader_or_source: Union[PDFReader, str, Path, bytes],
        document_name: Optional[str] = None,
        save_text_file: bool = True
    ) -> Dict[str, Any]:
        """
        Extract text from all pages of the document using the hybrid strategy.

        Returns structured summary containing:
            - document_name
            - total_pages
            - total_words
            - total_characters
            - extraction_method ("digital_text_layer", "ocr_fallback", or "hybrid")
            - text_file_path (Path where text is saved)
            - pages (list of per-page text & metrics)
            - full_text (consolidated string)
        """
        if isinstance(reader_or_source, PDFReader):
            reader = reader_or_source
        else:
            reader = PDFReader(reader_or_source, document_name=document_name)

        doc_stem = reader.document_stem
        total_pages = reader.total_pages()
        pages_result: List[Dict[str, Any]] = []

        total_words = 0
        total_chars = 0
        used_digital = False
        used_ocr = False

        # Open the PDF document
        with reader.open_pdf() as pdf:
            for page_idx in range(total_pages):
                page = pdf[page_idx]
                page_number = page_idx + 1

                # 1. Try digital text extraction
                page_text = page.get_text().strip()
                words = len(page_text.split())
                method = "digital_text_layer"

                # 2. If text is sparse, trigger OCR fallback
                if words < self.min_words_threshold:
                    logger.info(
                        f"Page {page_number} of '{reader.document_name}' has low text density ({words} words). Attempting OCR..."
                    )
                    pix = page.get_pixmap(dpi=self.dpi)
                    # Convert pixmap to PIL Image
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    
                    ocr_text = ""
                    if PYTESSERACT_AVAILABLE:
                        processed_img = self.preprocessor.preprocess(img)
                        try:
                            ocr_text = pytesseract.image_to_string(processed_img).strip()
                        except Exception as exc:
                            logger.warning(f"OCR execution failed on page {page_number}: {exc}")

                    if len(ocr_text.split()) > words:
                        page_text = ocr_text
                        words = len(page_text.split())
                        method = "ocr_fallback"
                        used_ocr = True
                    else:
                        used_digital = True
                else:
                    used_digital = True

                chars = len(page_text)
                total_words += words
                total_chars += chars

                pages_result.append({
                    "page_number": page_number,
                    "word_count": words,
                    "char_count": chars,
                    "method": method,
                    "text": page_text
                })

        # Determine overall extraction method
        if used_digital and used_ocr:
            overall_method = "hybrid"
        elif used_ocr:
            overall_method = "ocr_fallback"
        else:
            overall_method = "digital_text_layer"

        full_text = "\n\n".join([p["text"] for p in pages_result if p["text"]])

        # Save extracted text to outputs/text/<doc_stem>.txt
        text_file_path = None
        if save_text_file:
            text_file_path = TEXT_FOLDER / f"{doc_stem}.txt"
            text_file_path.parent.mkdir(parents=True, exist_ok=True)
            text_file_path.write_text(full_text, encoding="utf-8")
            logger.info(f"Saved extracted text to: {text_file_path}")

        return {
            "document_name": reader.document_name,
            "total_pages": total_pages,
            "total_words": total_words,
            "total_characters": total_chars,
            "extraction_method": overall_method,
            "text_file_path": str(text_file_path) if text_file_path else None,
            "pages": pages_result,
            "full_text": full_text
        }