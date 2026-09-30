import io
import os
import pytest
from fastapi.testclient import TestClient

# Ensure explicit test environment for test execution
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ML_INTERNAL_TOKEN", "dev-secret-internal-token-change-in-production")

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from app import app

client = TestClient(app)
INTERNAL_AUTH_HEADERS = {"X-Internal-Token": "dev-secret-internal-token-change-in-production"}


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
    for i in range(20):
        p1.draw_line(fitz.Point(100 + i, 500), fitz.Point(105 + i, 510))

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_health_endpoint():
    # Health endpoint is public for Docker/Kubernetes health checks
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_evaluate_missing_token_returns_401(sample_pdf_bytes):
    response = client.post(
        "/evaluate",
        files={"file": ("institution_approval.pdf", sample_pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_evaluate_wrong_token_returns_401(sample_pdf_bytes):
    response = client.post(
        "/evaluate",
        headers={"X-Internal-Token": "invalid-token"},
        files={"file": ("institution_approval.pdf", sample_pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_evaluate_non_ascii_token_returns_401(sample_pdf_bytes):
    # Pass raw bytes to simulate wire-level non-ASCII header without client-side httpx string encoding error
    response = client.post(
        "/evaluate",
        headers=[(b"x-internal-token", b"invalid-token-\xe9")],
        files={"file": ("institution_approval.pdf", sample_pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]

def test_evaluate_multipart_upload(sample_pdf_bytes):
    response = client.post(
        "/evaluate",
        headers=INTERNAL_AUTH_HEADERS,
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


def test_evaluate_json_filepath(sample_pdf_bytes, tmp_path, monkeypatch):
    pdf_file = tmp_path / "saved_doc.pdf"
    pdf_file.write_bytes(sample_pdf_bytes)

    monkeypatch.setattr("app.UPLOAD_FOLDER", tmp_path)

    response = client.post(
        "/evaluate",
        headers=INTERNAL_AUTH_HEADERS,
        json={"filePath": str(pdf_file), "documentId": "APP-1024"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["complianceEvaluation"]["overall_status"] == "COMPLIANT"


def test_evaluate_missing_payload():
    response = client.post(
        "/evaluate",
        headers=INTERNAL_AUTH_HEADERS
    )
    assert response.status_code == 400
    