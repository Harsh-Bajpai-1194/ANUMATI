import io
import json
import pytest
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from src.pipeline.verification_pipeline import VerificationPipeline


@pytest.fixture
def sample_aicte_pdf_bytes():
    """Generates a complete, compliant 2-page sample institutional PDF."""
    doc = fitz.open()

    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(
        (50, 80),
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)\n"
        "APPROVAL PROCESS HANDBOOK - INSTITUTIONAL COMPLIANCE\n"
        "Permanent Institute ID: 1-10987654321\n"
        "Application ID: 1-9876543210\n"
        "Academic Year: 2024-25\n"
        "College Code: EN-1024\n"
        "Campus Land Area: 4.5 Acres\n"
        "Student to Faculty Ratio: 1:15\n"
        "Total Faculty Count: 140\n"
        "Registrar Email: contact@institute.ac.in\n"
    )

    p2 = doc.new_page(width=595, height=842)
    p2.insert_text(
        (50, 80),
        "STATUTORY COMMITTEES COMPLIANCE DECLARATION:\n"
        "1. Anti-Ragging Committee constituted and active.\n"
        "2. Grievance Redressal Committee formed.\n"
        "3. Internal Complaint Committee (ICC) established.\n"
        "4. SC/ST Committee constituted.\n"
        "Authorized Signatory\n"
        "Principal / Director\n"
    )

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_verification_pipeline_end_to_end(sample_aicte_pdf_bytes):
    pipeline = VerificationPipeline(target_academic_year="2024-25")
    report = pipeline.verify_document(
        sample_aicte_pdf_bytes,
        document_name="test_institution_approval.pdf",
        save_report=True,
    )

    # Document details
    assert report["document"]["name"] == "test_institution_approval.pdf"
    assert report["document"]["total_pages"] == 2

    # Extraction
    assert report["text_extraction"]["total_words"] > 40
    assert report["text_extraction"]["method"] == "digital_text_layer"

    # Entities
    entities = report["extracted_entities"]
    assert entities["institute_id"] == "1-10987654321"
    assert entities["academic_year"] == "2024-25"
    assert entities["sfr_ratio"] == "1:15"

    # Compliance
    comp = report["compliance_evaluation"]
    assert comp["overall_status"] == "COMPLIANT"
    assert comp["compliance_score"] >= 0.8
    assert comp["passed_rules"] >= 4

    # Verify JSON report file was written
    report_file = Path(report["verification_metadata"]["report_file_path"])
    assert report_file.exists()
    saved_data = json.loads(report_file.read_text(encoding="utf-8"))
    assert saved_data["document"]["name"] == "test_institution_approval.pdf"


def test_verification_pipeline_non_compliant():
    # Empty / sparse document
    sparse_doc = fitz.open()
    p = sparse_doc.new_page()
    p.insert_text((50, 50), "Sports Festival Brochure 2024. No council details.")
    buf = io.BytesIO()
    sparse_doc.save(buf)
    sparse_doc.close()

    pipeline = VerificationPipeline()
    report = pipeline.verify_document(
        buf.getvalue(),
        document_name="sports_day.pdf",
        save_report=False,
    )

    assert report["compliance_evaluation"]["overall_status"] == "NON_COMPLIANT"
    assert report["compliance_evaluation"]["compliance_score"] < 0.5