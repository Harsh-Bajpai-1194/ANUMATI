import io
import pytest
from pathlib import Path
from PIL import Image

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from src.ocr.image_preprocessor import ImagePreprocessor
from src.ocr.ocr_engine import OCREngine
from src.preprocessing.pdf_reader import PDFReader


@pytest.fixture
def digital_pdf_bytes():
    """Generates an in-memory 2-page digital PDF with clear text."""
    doc = fitz.open()

    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(
        (50, 100),
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)\n"
        "Institutional Approval Handbook for Engineering & Technology.\n"
        "Faculty Requirements: Verified and compliant with Norms."
    )

    p2 = doc.new_page(width=595, height=842)
    p2.insert_text(
        (50, 100),
        "Official Declaration and Authorization Details.\n"
        "Principal Signature: Authorized.\n"
        "Seal of Institution Verified."
    )

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_image_preprocessor_pipeline():
    """Test image preprocessing produces a valid binary image."""
    preprocessor = ImagePreprocessor()
    test_img = Image.new("RGB", (200, 200), color=(240, 240, 240))
    processed = preprocessor.preprocess(test_img)

    assert processed.size == (200, 200)
    assert processed.mode == "1"  # Binary mode


def test_ocr_engine_digital_extraction(digital_pdf_bytes, tmp_path):
    """Test digital text extraction without requiring Tesseract."""
    engine = OCREngine(min_words_threshold=5)
    result = engine.process_document(
        digital_pdf_bytes,
        document_name="test_institution.pdf",
        save_text_file=True
    )

    assert result["document_name"] == "test_institution.pdf"
    assert result["total_pages"] == 2
    assert result["total_words"] > 20
    assert result["extraction_method"] == "digital_text_layer"
    assert "ALL INDIA COUNCIL" in result["full_text"]
    assert "Principal Signature" in result["full_text"]
    assert len(result["pages"]) == 2
    assert result["pages"][0]["method"] == "digital_text_layer"


def test_ocr_engine_text_file_saved(digital_pdf_bytes):
    """Test that extracted text file is written to outputs/text/."""
    engine = OCREngine()
    result = engine.process_document(
        digital_pdf_bytes,
        document_name="sample_verify.pdf",
        save_text_file=True
    )

    out_file = Path(result["text_file_path"])
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "AICTE" in content