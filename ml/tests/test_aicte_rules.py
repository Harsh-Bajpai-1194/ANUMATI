import pytest
from src.rules.text_cleaner import TextCleaner
from src.rules.aicte_rules import AICTERuleEngine


def test_text_cleaner_line_wrap_and_whitespace():
    raw = "The insti-\ntution has com-\npleted all req-\nuirements.   Multiple   spaces.\n\n\n\nNew lines."
    cleaned = TextCleaner.clean_text(raw)
    assert "institution has completed all requirements." in cleaned
    assert "Multiple spaces." in cleaned
    assert "\n\n\n" not in cleaned


def test_entity_extraction_compliant():
    text = (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION\n"
        "Permanent Institute ID: 1-10987654321\n"
        "Application ID: 1-9876543210\n"
        "Academic Year: 2024-25\n"
        "Student Faculty Ratio: 1:15\n"
        "Land Area: 5.5 Acres\n"
        "Total Faculty: 120\n"
        "Contact: registrar@examplecollege.edu.in, +91 9876543210\n"
    )
    entities = TextCleaner.extract_entities(text)
    assert entities["has_aicte_mention"] is True
    assert entities["institute_id"] == "1-10987654321"
    assert entities["academic_year"] == "2024-25"
    assert entities["sfr_ratio"] == "1:15"
    assert entities["land_value"] == 5.5
    assert entities["total_faculty"] == 120
    assert "registrar@examplecollege.edu.in" in entities["emails"]


def test_aicte_rule_engine_full_compliance():
    sample_text = (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)\n"
        "Permanent Institute ID: 1-10987654321\n"
        "Academic Year: 2024-25\n"
        "Student Faculty Ratio: 1:15\n"
        "Campus Land Area: 4.2 Acres\n"
        "Statutory Committees Formed:\n"
        "1. Anti-Ragging Committee constituted.\n"
        "2. Grievance Redressal Committee active.\n"
        "3. Internal Complaint Committee (ICC) formed.\n"
        "4. SC/ST Committee constituted.\n"
    )

    engine = AICTERuleEngine()
    result = engine.evaluate_text(sample_text)

    assert result["overall_status"] == "COMPLIANT"
    assert result["compliance_score"] >= 0.8
    assert result["extracted_entities"]["institute_id"] == "1-10987654321"

    # Check committees passed
    comm_rule = next(r for r in result["rules"] if r["rule_id"] == "AICTE-R03-COMMITTEES")
    assert comm_rule["status"] == "PASSED"

    # Check land passed
    land_rule = next(r for r in result["rules"] if r["rule_id"] == "AICTE-R05-LAND")
    assert land_rule["status"] == "PASSED"


def test_aicte_rule_engine_non_compliant():
    sparse_text = "Random College Brochure. Welcome students to admission 2024."
    engine = AICTERuleEngine()
    result = engine.evaluate_text(sparse_text)

    assert result["overall_status"] == "NON_COMPLIANT"
    assert result["compliance_score"] < 0.5

    header_rule = next(r for r in result["rules"] if r["rule_id"] == "AICTE-R01-HEADER")
    assert header_rule["status"] == "FAILED"

    comm_rule = next(r for r in result["rules"] if r["rule_id"] == "AICTE-R03-COMMITTEES")
    assert comm_rule["status"] == "FAILED"


def test_aicte_rule_engine_invalid_sfr():
    sample_text = (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)\n"
        "Permanent Institute ID: 1-10987654321\n"
        "Academic Year: 2024-25\n"
        "Student Faculty Ratio: 1:35\n"  # Invalid ratio (> 1:20)
    )

    engine = AICTERuleEngine()
    result = engine.evaluate_text(sample_text)

    sfr_rule = next(r for r in result["rules"] if r["rule_id"] == "AICTE-R04-SFR")
    assert sfr_rule["status"] == "FAILED"
    assert "exceeds maximum permissible" in sfr_rule["details"]