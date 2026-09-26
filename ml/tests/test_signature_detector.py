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
    # Create image with blue stamp patch
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    for x in range(50, 100):
        for y in range(50, 100):
            img.putpixel((x, y), (30, 40, 220))  # Blue ink

    analysis = detector._detect_ink_and_seals_in_image(img)
    assert analysis["stamp_detected"] is True
    assert analysis["stamp_confidence"] > 0.5


def test_detect_signature_in_pdf():
    detector = SignatureDetector()

    # Create dummy PDF with signature text and drawing paths
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 700), "Authorized Signatory: Principal / Director")

    # Add 25 vector lines to simulate signature strokes
    for i in range(25):
        page.draw_line(fitz.Point(100 + i, 720), fitz.Point(105 + i, 730))

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    result = detector.detect_signatures_in_pdf(buf.getvalue())
    assert result["signature_detected"] is True
    assert result["confidence"] >= 0.8
    assert result["status"] == "verified"