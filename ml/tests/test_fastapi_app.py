import io
import pytest
from fastapi.testclient import TestClient

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from app import app

client = TestClient(app)


@pytest.fixture
def sample_pdf_bytes():
    """Generates an in-memory compliant institutional PDF."""
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(
        (50, 80),
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)\n"
        "Approval Process Handbook - Extension of Approval\n"
        "Permanent Institute ID: 1-10987654321\n"
        "Academic Year: 2024-25\n"
        "Student to Faculty Ratio: 1:15\n"
        "Campus Land Area: 4.5 Acres\n"
        "Statutory Committees:\n"
        "1. Anti-Ragging Committee active.\n"
        "2. Grievance Redressal Committee formed.\n"
        "3. Internal Complaint Committee (ICC) established.\n"
        "4. SC/ST Committee constituted.\n"
        "Authorized Signatory: Principal / Director"
    )
    # Add vector lines for signature
    for i in range(20):
        p1.draw_line(fitz.Point(100 + i, 500), fitz.Point(105 + i, 510))

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_evaluate_multipart_upload(sample_pdf_bytes):
    response = client.post(
        "/evaluate",
        files={"file": ("institution_approval.pdf", sample_pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["document"]["name"] == "institution_approval.pdf"
    assert data["classification"]["category"] == "AICTE_APPROVAL_LETTER"
    assert data["textExtraction"]["totalWords"] > 20
    assert data["complianceEvaluation"]["overall_status"] == "COMPLIANT"
    assert "anomalyDetection" in data
    assert "signatureVerification" in data


def test_evaluate_json_filepath(sample_pdf_bytes, tmp_path):
    pdf_file = tmp_path / "saved_doc.pdf"
    pdf_file.write_bytes(sample_pdf_bytes)

    response = client.post(
        "/evaluate",
        json={"filePath": str(pdf_file), "documentId": "APP-1024"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["complianceEvaluation"]["overall_status"] == "COMPLIANT"


def test_evaluate_missing_payload():
    response = client.post("/evaluate")
    assert response.status_code == 400