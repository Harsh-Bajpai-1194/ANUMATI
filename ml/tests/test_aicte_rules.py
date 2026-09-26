import pytest
from src.rules.text_cleaner import TextCleaner
from src.rules.aicte_rules import AICTERuleEngine


def test_text_cleaner_line_wrap_and_whitespace():
    raw = (
        "The insti-\ntution has com-\npleted all req-\nuirements. "
        "Anti-\nRagging Committee active for 2024-\n25.   Multiple   spaces.\n\n\n\nNew lines."
    )
    cleaned = TextCleaner.clean_text(raw)
    assert "institution has completed all requirements." in cleaned
    assert "Anti-Ragging Committee" in cleaned
    assert "2024-25" in cleaned
    assert "Multiple spaces." in cleaned
    assert "\n\n\n" not in cleaned


def test_entity_extraction_sq_m_and_labels():
    text = (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION\n"
        "Permanent Institute ID: 1-10987654321\n"
        "Application ID: 1-9876543210\n"
        "Academic Year: 2024-25\n"
        "Student Faculty Ratio: 1:15\n"
        "Land Area: 10000 sq m\n"
        "Total Faculty: 120\n"
        "Contact: registrar@examplecollege.edu.in, +91 9876543210\n"
    )
    entities = TextCleaner.extract_entities(text)
    assert entities["has_aicte_mention"] is True
    assert entities["institute_id"] == "1-10987654321"
    assert entities["application_id"] == "1-9876543210"
    assert entities["academic_year"] == "2024-25"
    assert entities["sfr_ratio"] == "1:15"
    assert entities["land_value"] == 10000.0
    assert "sq m" in entities["land_unit"]
    assert entities["total_faculty"] == 120
    assert "registrar@examplecollege.edu.in" in entities["emails"]


def test_application_id_not_mistaken_for_institute_id():
    text = "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION\nApplication ID: 1-9876543210\n"
    entities = TextCleaner.extract_entities(text)
    assert entities["application_id"] == "1-9876543210"
    assert entities["institute_id"] is None


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

    engine = AICTERuleEngine(target_academic_year="2024-25")
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


def test_negated_committee_not_counted_as_formed():
    text = (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)\n"
        "Permanent Institute ID: 1-10987654321\n"
        "Academic Year: 2024-25\n"
        "Student Faculty Ratio: 1:15\n"
        "Campus Land Area: 2.0 Acres\n"
        "No Anti-Ragging Committee has been formed yet.\n"
        "Grievance Redressal Committee: not available.\n"
    )
    engine = AICTERuleEngine()
    result = engine.evaluate_text(text)
    comm_rule = next(r for r in result["rules"] if r["rule_id"] == "AICTE-R03-COMMITTEES")
    assert comm_rule["status"] == "FAILED"


def test_aicte_rule_engine_inverted_and_invalid_sfr():
    # 30:1 is 30 students per faculty -> non-compliant
    sample_text = (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)\n"
        "Permanent Institute ID: 1-10987654321\n"
        "Academic Year: 2024-25\n"
        "Student Faculty Ratio: 30:1\n"
    )
    engine = AICTERuleEngine()
    result = engine.evaluate_text(sample_text)

    sfr_rule = next(r for r in result["rules"] if r["rule_id"] == "AICTE-R04-SFR")
    assert sfr_rule["status"] == "FAILED"
    assert "exceeds maximum permissible" in sfr_rule["details"]


def test_academic_year_target_mismatch():
    sample_text = (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)\n"
        "Permanent Institute ID: 1-10987654321\n"
        "Academic Year: 2023-24\n"
    )
    engine = AICTERuleEngine(target_academic_year="2025-26")
    result = engine.evaluate_text(sample_text)

    ay_rule = next(r for r in result["rules"] if r["rule_id"] == "AICTE-R02-ACADEMIC_YEAR")
    assert ay_rule["status"] == "FAILED"
    assert "does not match target" in ay_rule["details"]