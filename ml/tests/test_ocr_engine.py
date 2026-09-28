import io
import pytest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from src.ocr.image_preprocessor import ImagePreprocessor
from src.ocr.ocr_engine import OCREngine, OCREngineError
from unittest.mock import patch, MagicMock
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


@pytest.fixture
def scanned_blank_pdf_bytes():
    """Generates an in-memory 1-page PDF with no digital text (simulates scanned page)."""
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_image_preprocessor_pipeline():
    """Test image preprocessing produces a valid grayscale and binary image."""
    preprocessor = ImagePreprocessor()
    test_img = Image.new("RGB", (200, 200), color=(240, 240, 240))

    # Grayscale mode (default for Tesseract)
    processed_gray = preprocessor.preprocess(test_img, apply_binarization=False)
    assert processed_gray.size == (200, 200)
    assert processed_gray.mode == "L"

    # Binary mode
    processed_bin = preprocessor.preprocess(test_img, apply_binarization=True)
    assert processed_bin.mode == "1"


def test_image_preprocessor_invalid_type():
    """Verify ImagePreprocessor raises TypeError on invalid source input."""
    preprocessor = ImagePreprocessor()
    with pytest.raises(TypeError, match="Unsupported image source type"):
        preprocessor.preprocess(12345)


def test_ocr_engine_digital_extraction(digital_pdf_bytes):
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
    """Test that extracted text file is written to outputs/text/<doc_stem>/extracted_text.txt."""
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

def test_ocr_fallback_with_mocked_pytesseract(scanned_blank_pdf_bytes):
    """Test that low-density/scanned pages trigger OCR fallback when Tesseract is available."""
    mock_ocr_output = (
        "AICTE SCANNED INSTITUTION APPROVAL PROCESS HANDBOOK\n"
        "Permanent Institute ID: 1-9988776655\n"
        "Faculty count verified."
    )

    mock_tesseract = MagicMock()
    mock_tesseract.image_to_string.return_value = mock_ocr_output

    with patch("src.ocr.ocr_engine.PYTESSERACT_AVAILABLE", True), \
         patch("src.ocr.ocr_engine.pytesseract", mock_tesseract):
        engine = OCREngine(min_words_threshold=15)
        result = engine.process_document(scanned_blank_pdf_bytes, document_name="scanned_doc.pdf")

        assert result["extraction_method"] == "ocr_fallback"
        assert result["total_words"] > 5
        assert "AICTE SCANNED INSTITUTION" in result["full_text"]
        assert result["pages"][0]["method"] == "ocr_fallback"

def test_ocr_graceful_degradation_without_tesseract(scanned_blank_pdf_bytes):
    """Test graceful handling when pytesseract is not available."""
    with patch("src.ocr.ocr_engine.PYTESSERACT_AVAILABLE", False):
        engine = OCREngine(min_words_threshold=15)
        result = engine.process_document(scanned_blank_pdf_bytes, document_name="no_tesseract.pdf")

        assert result["ocr_engine_available"] is False
        assert result["extraction_method"] == "unreadable_or_empty"
        assert result["total_words"] == 0

def test_ocr_engine_error_on_invalid_source():
    """Verify OCREngineError is raised for invalid inputs."""
    engine = OCREngine()
    with pytest.raises(OCREngineError, match="Unsupported reader or source type"):
        engine.process_document(12345)

def test_document_stem_sanitizes_windows_backslashes():
    """Verify document_stem handles Windows backslash path traversal."""
    # 1. Backslash path with valid filename should sanitize to stem
    reader = PDFReader(b"%PDF-1.4-sample", document_name="..\\..\\evil_doc.pdf")
    assert reader.document_stem == "evil_doc"

    # 2. Bare backslash traversal must raise ValueError
    reader_traversal = PDFReader(b"%PDF-1.4-sample", document_name="..\\..\\..")
    with pytest.raises(ValueError, match="document_name must identify a valid file name"):
        _ = reader_traversal.document_stem


def test_ocr_engine_accepts_bytesio(digital_pdf_bytes):
    """Verify OCREngine.process_document accepts io.BytesIO stream directly."""
    engine = OCREngine(min_words_threshold=5)
    stream = io.BytesIO(digital_pdf_bytes)
    result = engine.process_document(stream, document_name="streamed_report.pdf", save_text_file=False)

    assert result["total_pages"] == 2
    assert result["extraction_method"] == "digital_text_layer"
    assert "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION" in result["full_text"]
