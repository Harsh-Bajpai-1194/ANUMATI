import io
import pytest
from PIL import Image

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from src.signature.signature_detector import SignatureDetector


def test_detect_blue_stamp_image():
    detector = SignatureDetector()
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    for x in range(50, 100):
        for y in range(50, 100):
            img.putpixel((x, y), (30, 40, 220))  # Blue ink

    analysis = detector._detect_ink_and_seals_in_image(img)
    assert analysis["stamp_detected"] is True
    assert analysis["stamp_confidence"] > 0.5


def test_text_only_page_not_found():
    """
    Test that a text-only page (even with dense text and signature keyword)
    reports 'not_found' and does not trigger false positive signatures.
    """
    detector = SignatureDetector()

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Add dense text paragraphs
    for i in range(20):
        page.insert_text((50, 80 + i * 25), "AICTE Statutory document dense paragraph text without signatures. " * 2)
    # Add signature keyword without any scribble
    page.insert_text((50, 720), "Authorized Signatory: Principal / Director")

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    result = detector.detect_signatures_in_pdf(buf.getvalue())
    assert result["signature_detected"] is False
    assert result["status"] == "not_found"


def test_scribble_above_authorized_signatory_candidate():
    """
    Test that a drawn scribble placed above 'Authorized Signatory'
    is detected as a signature candidate.
    """
    detector = SignatureDetector()

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 720), "Authorized Signatory: Principal / Director")

    # Add vector lines above the keyword to simulate a signature scribble
    for i in range(15):
        page.draw_line(fitz.Point(70 + i * 4, 660 + (i % 3) * 6), fitz.Point(75 + i * 4, 675))

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    result = detector.detect_signatures_in_pdf(buf.getvalue())
    assert result["signature_detected"] is True
    assert result["confidence"] >= 0.8
    assert result["status"] == "signature_candidate"


def test_dense_scanned_text_no_keyword_not_found():
    """
    Test that a page with dense text and no signature keyword reports 'not_found'.
    """
    detector = SignatureDetector()

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    for i in range(30):
        page.insert_text((50, 50 + i * 22), "Standard academic curriculum and approval guideline section body text. " * 2)

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    result = detector.detect_signatures_in_pdf(buf.getvalue())
    assert result["signature_detected"] is False
    assert result["status"] == "not_found"
    