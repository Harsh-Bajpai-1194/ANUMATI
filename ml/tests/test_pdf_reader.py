import io
import fitz
import pytest
from pathlib import Path
from src.preprocessing.pdf_reader import (
    PDFReader,
    CorruptedPDFError,
    EmptyPDFError,
)


@pytest.fixture
def sample_pdf_bytes():
    """Generates an in-memory 2-page PDF document for testing."""
    doc = fitz.open()
    
    # Page 1
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 100), "ANUMATI AICTE Approval Document - Page 1")

    # Page 2
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 100), "Institutional Verification Details - Page 2")

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_pdf_reader_from_bytes(sample_pdf_bytes, tmp_path):
    reader = PDFReader(sample_pdf_bytes, document_name="test_doc.pdf")
    
    # Test page count
    assert reader.total_pages() == 2

    # Test metadata
    meta = reader.get_metadata()
    assert meta["total_pages"] == 2
    assert meta["document_name"] == "test_doc.pdf"

    # Test text extraction
    text = reader.extract_text()
    assert "ANUMATI AICTE Approval" in text
    assert "Institutional Verification Details" in text

    # Test image extraction
    out_dir = tmp_path / "images"
    images = reader.extract_images(output_dir=out_dir, dpi=150)
    assert len(images) == 2
    assert (out_dir / "page_1.png").exists()
    assert (out_dir / "page_2.png").exists()


def test_pdf_reader_corrupted_bytes():
    corrupt_bytes = b"%PDF-invalid-bytes-header"
    reader = PDFReader(corrupt_bytes, document_name="corrupt.pdf")
    with pytest.raises(CorruptedPDFError):
        reader.open_pdf()


def test_pdf_reader_empty_stream():
    reader = PDFReader(b"", document_name="empty.pdf")
    with pytest.raises(CorruptedPDFError):
        reader.open_pdf()