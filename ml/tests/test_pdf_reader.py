import io
import pytest
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from src.preprocessing.pdf_reader import (
    PDFReader,
    PDFProcessingError,
    EncryptedPDFError,
    CorruptedPDFError,
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

    # Page count
    assert reader.total_pages() == 2

    # Metadata
    meta = reader.get_metadata()
    assert meta["total_pages"] == 2
    assert meta["document_name"] == "test_doc.pdf"

    # Text extraction
    text = reader.extract_text()
    assert "ANUMATI AICTE Approval" in text
    assert "Institutional Verification Details" in text

    # Image extraction
    out_dir = tmp_path / "images"
    images = reader.extract_images(output_dir=out_dir, dpi=150)
    assert len(images) == 2
    assert (out_dir / "page_1.png").exists()
    assert (out_dir / "page_2.png").exists()


def test_pdf_reader_bytesio_input(sample_pdf_bytes):
    """Test ingestion directly from an io.BytesIO stream."""
    stream = io.BytesIO(sample_pdf_bytes)
    reader = PDFReader(stream, document_name="stream_doc.pdf")
    assert reader.total_pages() == 2
    assert "ANUMATI AICTE" in reader.extract_text()


def test_pdf_reader_missing_file():
    """Test that a non-existent file path raises FileNotFoundError."""
    reader = PDFReader("non_existent_file_xyz.pdf")
    with pytest.raises(FileNotFoundError):
        reader.open_pdf()


def test_pdf_reader_unsupported_image_format(sample_pdf_bytes, tmp_path):
    """Test that requesting an unsupported format raises PDFProcessingError."""
    reader = PDFReader(sample_pdf_bytes)
    with pytest.raises(PDFProcessingError, match="Unsupported image format"):
        reader.extract_images(output_dir=tmp_path, image_format="bmp")


def test_pdf_reader_invalid_page_indices(sample_pdf_bytes, tmp_path):
    """Test out-of-range page indices are safely skipped without crashing."""
    reader = PDFReader(sample_pdf_bytes)
    images = reader.extract_images(output_dir=tmp_path, pages=[0, 99, -5])
    assert len(images) == 1
    assert (tmp_path / "page_1.png").exists()


def test_pdf_reader_encrypted(tmp_path):
    """Test that password-protected PDF raises EncryptedPDFError."""
    doc = fitz.open()
    doc.new_page()
    encrypted_path = tmp_path / "protected.pdf"

    doc.save(
        str(encrypted_path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="adminpass",
        user_pw="secretpass",
    )
    doc.close()

    reader = PDFReader(encrypted_path)
    with pytest.raises(EncryptedPDFError):
        reader.open_pdf()


def test_pdf_reader_corrupted_bytes():
    corrupt_bytes = b"%PDF-invalid-bytes-header"
    reader = PDFReader(corrupt_bytes, document_name="corrupt.pdf")
    with pytest.raises(CorruptedPDFError):
        reader.open_pdf()


def test_pdf_reader_empty_stream():
    reader = PDFReader(b"", document_name="empty.pdf")
    with pytest.raises(CorruptedPDFError):
        reader.open_pdf()