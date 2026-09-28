import pytest
from src.classification.document_classifier import DocumentClassifier


def test_classify_aicte_approval_letter():
    classifier = DocumentClassifier()
    text = (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)\n"
        "Approval Process Handbook - Extension of Approval.\n"
        "Permanent Institute ID: 1-12345678. Sanctioned Intake Approved."
    )
    result = classifier.classify_text(text)
    assert result["category"] == "AICTE_APPROVAL_LETTER"
    assert result["confidence"] >= 0.5
    assert "aicte" in result["matched_signals"]


def test_classify_faculty_list():
    classifier = DocumentClassifier()
    text = (
        "Institutional Teaching Staff and Faculty List.\n"
        "1. Dr. John Doe - Professor, Department of Computer Science, Ph.D.\n"
        "2. Jane Smith - Assistant Professor, Pay Scale, SFR Compliant."
    )
    result = classifier.classify_text(text)
    assert result["category"] == "FACULTY_LIST"
    assert "professor" in result["matched_signals"]


def test_classify_land_document():
    classifier = DocumentClassifier()
    text = (
        "Land Ownership Deed and Demarcation Certificate.\n"
        "Khasra Survey Number: 104/2. Total Campus Land Area: 5.5 Acres.\n"
        "Registered with Sub-Registrar Office."
    )
    result = classifier.classify_text(text)
    assert result["category"] == "LAND_DOCUMENT"
    assert "acres" in result["matched_signals"]


def test_classify_unknown_text():
    classifier = DocumentClassifier()
    text = "General sports day event invite for all participants."
    result = classifier.classify_text(text)
    assert result["category"] == "OTHER"