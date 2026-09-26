import re
import logging
from typing import Dict, List, Optional, Any

from .text_cleaner import TextCleaner

logger = logging.getLogger("anumati-ml.aicte_rules")


class AICTERuleEngine:
    """
    AICTE Approval Process Handbook (APH) Rule Verification Engine.
    Validates institutional disclosures, ratios, mandatory statutory committees,
    and accreditation norms deterministically.
    """

    MANDATORY_COMMITTEES = [
        {
            "code": "ANTI_RAGGING",
            "name": "Anti-Ragging Committee",
            "pattern": r"anti[-\s]*ragging\s*(?:committee|squad)?",
        },
        {
            "code": "GRIEVANCE_REDRESSAL",
            "name": "Grievance Redressal Committee",
            "pattern": r"grievance\s*redressal\s*(?:committee|mechanism)?",
        },
        {
            "code": "INTERNAL_COMPLAINTS",
            "name": "Internal Complaint Committee (ICC)",
            "pattern": r"internal\s*complaint\s*committee|\bicc\b",
        },
        {
            "code": "SC_ST_COMMITTEE",
            "name": "SC/ST Committee",
            "pattern": r"sc\s*/\s*st\s*(?:committee|cell)?",
        },
    ]

    def __init__(self, target_academic_year: Optional[str] = None):
        self.target_academic_year = target_academic_year

    def evaluate_text(self, raw_text: str) -> Dict[str, Any]:
        """
        Run all statutory AICTE compliance checks against the provided text.
        """
        clean_text = TextCleaner.clean_text(raw_text)
        entities = TextCleaner.extract_entities(clean_text)

        rule_results: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # Rule 1: AICTE Header & Identifier Verification
        # -------------------------------------------------------------
        has_aicte = entities["has_aicte_mention"]
        has_pid = bool(entities["institute_id"])

        if has_aicte and has_pid:
            rule_results.append({
                "rule_id": "AICTE-R01-HEADER",
                "name": "AICTE Recognition & Permanent Institute ID",
                "status": "PASSED",
                "severity": "critical",
                "details": f"AICTE reference confirmed with Institute ID: {entities['institute_id']}",
            })
        elif has_aicte:
            rule_results.append({
                "rule_id": "AICTE-R01-HEADER",
                "name": "AICTE Recognition & Permanent Institute ID",
                "status": "WARNING",
                "severity": "high",
                "details": "AICTE Council mentioned, but Permanent Institute ID (PID) was not detected.",
            })
        else:
            rule_results.append({
                "rule_id": "AICTE-R01-HEADER",
                "name": "AICTE Recognition & Permanent Institute ID",
                "status": "FAILED",
                "severity": "critical",
                "details": "No mention of AICTE Council or official Institute ID found in the document.",
            })

        # -------------------------------------------------------------
        # Rule 2: Academic Year Validation
        # -------------------------------------------------------------
        ay = entities["academic_year"]
        if ay:
            rule_results.append({
                "rule_id": "AICTE-R02-ACADEMIC_YEAR",
                "name": "Academic Year Specification",
                "status": "PASSED",
                "severity": "medium",
                "details": f"Document specifies Academic Year: {ay}",
            })
        else:
            rule_results.append({
                "rule_id": "AICTE-R02-ACADEMIC_YEAR",
                "name": "Academic Year Specification",
                "status": "FAILED",
                "severity": "medium",
                "details": "No valid academic year format (e.g. 2024-25) detected in document text.",
            })

        # -------------------------------------------------------------
        # Rule 3: Mandatory Statutory Committees
        # -------------------------------------------------------------
        missing_committees = []
        found_committees = []

        for comm in self.MANDATORY_COMMITTEES:
            if re.search(comm["pattern"], clean_text, re.IGNORECASE):
                found_committees.append(comm["name"])
            else:
                missing_committees.append(comm["name"])

        if not missing_committees:
            rule_results.append({
                "rule_id": "AICTE-R03-COMMITTEES",
                "name": "Mandatory Statutory Committees",
                "status": "PASSED",
                "severity": "high",
                "details": f"All 4 mandatory committees detected: {', '.join(found_committees)}",
            })
        elif len(found_committees) > 0:
            rule_results.append({
                "rule_id": "AICTE-R03-COMMITTEES",
                "name": "Mandatory Statutory Committees",
                "status": "WARNING",
                "severity": "high",
                "details": f"Missing committees: {', '.join(missing_committees)}. Found: {', '.join(found_committees)}",
            })
        else:
            rule_results.append({
                "rule_id": "AICTE-R03-COMMITTEES",
                "name": "Mandatory Statutory Committees",
                "status": "FAILED",
                "severity": "high",
                "details": "None of the mandatory statutory committees were mentioned in the document.",
            })

        # -------------------------------------------------------------
        # Rule 4: Student-to-Faculty Ratio (SFR) Compliance
        # -------------------------------------------------------------
        sfr = entities["sfr_ratio"]
        if sfr:
            parts = re.split(r"[:/]", sfr)
            try:
                num = float(parts[1]) if len(parts) > 1 else float(parts[0])
                if num <= 20.0:
                    rule_results.append({
                        "rule_id": "AICTE-R04-SFR",
                        "name": "Student-to-Faculty Ratio (SFR)",
                        "status": "PASSED",
                        "severity": "high",
                        "details": f"Document claims compliant SFR ratio of 1:{int(num)} (Norm: <= 1:20)",
                    })
                else:
                    rule_results.append({
                        "rule_id": "AICTE-R04-SFR",
                        "name": "Student-to-Faculty Ratio (SFR)",
                        "status": "FAILED",
                        "severity": "high",
                        "details": f"SFR ratio 1:{num} exceeds maximum permissible AICTE limit of 1:20",
                    })
            except (ValueError, IndexError):
                rule_results.append({
                    "rule_id": "AICTE-R04-SFR",
                    "name": "Student-to-Faculty Ratio (SFR)",
                    "status": "WARNING",
                    "severity": "medium",
                    "details": f"SFR mentioned as '{sfr}' but numeric ratio could not be parsed.",
                })
        else:
            rule_results.append({
                "rule_id": "AICTE-R04-SFR",
                "name": "Student-to-Faculty Ratio (SFR)",
                "status": "INSUFFICIENT_DATA",
                "severity": "medium",
                "details": "No explicit Student-to-Faculty Ratio (SFR) disclosure found in text.",
            })

        # -------------------------------------------------------------
        # Rule 5: Land Area Requirements
        # -------------------------------------------------------------
        land_val = entities["land_value"]
        land_unit = entities["land_unit"]

        if land_val is not None:
            # AICTE minimum land requirement is generally >= 1.5 - 2.5 acres for urban, up to 4.0 - 5.0 in rural
            if "acre" in land_unit and land_val >= 1.5:
                land_status = "PASSED"
                land_details = f"Land area ({land_val} Acres) complies with minimum campus acreage guidelines."
            elif "hectare" in land_unit and land_val >= 0.6:
                land_status = "PASSED"
                land_details = f"Land area ({land_val} Hectares) complies with minimum campus acreage guidelines."
            elif land_val < 1.0 and "acre" in land_unit:
                land_status = "FAILED"
                land_details = f"Land area ({land_val} Acres) is below statutory AICTE requirements."
            else:
                land_status = "PASSED"
                land_details = f"Campus land disclosure recorded: {entities['land_area']}."

            rule_results.append({
                "rule_id": "AICTE-R05-LAND",
                "name": "Institutional Land Area Disclosure",
                "status": land_status,
                "severity": "medium",
                "details": land_details,
            })
        else:
            rule_results.append({
                "rule_id": "AICTE-R05-LAND",
                "name": "Institutional Land Area Disclosure",
                "status": "INSUFFICIENT_DATA",
                "severity": "low",
                "details": "No explicit campus land area figure was extracted.",
            })

        # Calculate Overall Compliance Score
        passed_count = sum(1 for r in rule_results if r["status"] == "PASSED")
        total_evaluable = sum(1 for r in rule_results if r["status"] != "INSUFFICIENT_DATA")
        compliance_score = round(passed_count / total_evaluable, 2) if total_evaluable > 0 else 0.0

        if compliance_score >= 0.8:
            overall_status = "COMPLIANT"
        elif compliance_score >= 0.5:
            overall_status = "PARTIALLY_COMPLIANT"
        else:
            overall_status = "NON_COMPLIANT"

        return {
            "overall_status": overall_status,
            "compliance_score": compliance_score,
            "total_rules_evaluated": len(rule_results),
            "passed_rules": passed_count,
            "extracted_entities": entities,
            "rules": rule_results,
        }