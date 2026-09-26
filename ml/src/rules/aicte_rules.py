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

    REQUIRED_RULE_IDS = {
        "AICTE-R01-HEADER",
        "AICTE-R02-ACADEMIC_YEAR",
        "AICTE-R03-COMMITTEES",
        "AICTE-R04-SFR",
    }

    def __init__(self, target_academic_year: Optional[str] = None):
        self.target_academic_year = target_academic_year

    @staticmethod
    def _is_negated(text: str, match_start: int) -> bool:
        """Checks if a match is preceded or succeeded by a negation clause."""
        snippet_start = max(0, match_start - 60)
        snippet_end = min(len(text), match_start + 80)
        snippet = text[snippet_start:snippet_end].lower()

        negation_terms = [
            r"\bno\b",
            r"\bnot\b",
            r"\bnil\b",
            r"\bnone\b",
            r"\bwithout\b",
            r"\babsent\b",
            r"\bnot\s+formed\b",
            r"\bnot\s+constituted\b",
            r"\bnot\s+available\b",
        ]
        return any(re.search(term, snippet) for term in negation_terms)

    def evaluate_text(self, raw_text: str) -> Dict[str, Any]:
        """
        Run statutory AICTE compliance checks against provided text.
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
            if self.target_academic_year:
                if ay == self.target_academic_year or self.target_academic_year in ay:
                    ay_status = "PASSED"
                    ay_details = f"Document specifies matching Academic Year: {ay}"
                else:
                    ay_status = "FAILED"
                    ay_details = f"Detected Academic Year '{ay}' does not match target '{self.target_academic_year}'."
            else:
                ay_status = "PASSED"
                ay_details = f"Document specifies Academic Year: {ay}"

            rule_results.append({
                "rule_id": "AICTE-R02-ACADEMIC_YEAR",
                "name": "Academic Year Specification",
                "status": ay_status,
                "severity": "medium",
                "details": ay_details,
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
            matches = list(re.finditer(comm["pattern"], clean_text, re.IGNORECASE))
            # Confirm at least one match has affirmative context (not negated)
            affirmative_match = any(not self._is_negated(clean_text, m.start()) for m in matches)

            if matches and affirmative_match:
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
                v1, v2 = float(parts[0]), float(parts[1])
                if v1 <= 0 or v2 <= 0:
                    raise ValueError("Non-positive counts")

                # Parse ratio orientation (e.g. 1:15 vs 15:1 vs 30:1)
                students, faculty = (v1, v2) if v1 >= v2 else (v2, v1)
                ratio_value = students / faculty

                if ratio_value <= 20.0:
                    rule_results.append({
                        "rule_id": "AICTE-R04-SFR",
                        "name": "Student-to-Faculty Ratio (SFR)",
                        "status": "PASSED",
                        "severity": "high",
                        "details": f"Document claims compliant SFR ratio of {int(ratio_value)}:1 (Norm: <= 20:1)",
                    })
                else:
                    rule_results.append({
                        "rule_id": "AICTE-R04-SFR",
                        "name": "Student-to-Faculty Ratio (SFR)",
                        "status": "FAILED",
                        "severity": "high",
                        "details": f"SFR ratio {round(ratio_value, 1)}:1 exceeds maximum permissible AICTE limit of 20:1",
                    })
            except (ValueError, IndexError, ZeroDivisionError):
                rule_results.append({
                    "rule_id": "AICTE-R04-SFR",
                    "name": "Student-to-Faculty Ratio (SFR)",
                    "status": "WARNING",
                    "severity": "medium",
                    "details": f"SFR mentioned as '{sfr}' but contains non-positive or invalid numeric values.",
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
        land_unit = entities["land_unit"] or ""

        if land_val is not None:
            # 1.5 Acres / 0.6 Hectares / ~6070 Sq. Meters
            if "acre" in land_unit:
                if land_val >= 1.5:
                    land_status = "PASSED"
                    land_details = f"Land area ({land_val} Acres) complies with minimum campus acreage guidelines."
                else:
                    land_status = "FAILED"
                    land_details = f"Land area ({land_val} Acres) is below minimum requirement of 1.5 Acres."
            elif "hectare" in land_unit:
                if land_val >= 0.6:
                    land_status = "PASSED"
                    land_details = f"Land area ({land_val} Hectares) complies with minimum campus acreage guidelines."
                else:
                    land_status = "FAILED"
                    land_details = f"Land area ({land_val} Hectares) is below minimum requirement of 0.6 Hectares."
            elif any(u in land_unit for u in ["sq", "meter", "m"]):
                if land_val >= 6000:
                    land_status = "PASSED"
                    land_details = f"Land area ({land_val} sq m) complies with campus area norms."
                else:
                    land_status = "FAILED"
                    land_details = f"Land area ({land_val} sq m) is below minimum norm of 6000 sq m."
            else:
                land_status = "WARNING"
                land_details = f"Unrecognized land unit '{land_unit}' with value {land_val}."

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

        # -------------------------------------------------------------
        # Honest Compliance Scoring & Gated Status
        # -------------------------------------------------------------
        passed_count = sum(1 for r in rule_results if r["status"] == "PASSED")
        # Ensure required rules with INSUFFICIENT_DATA stay in denominator
        evaluable_rules = [
            r for r in rule_results
            if r["status"] != "INSUFFICIENT_DATA" or r["rule_id"] in self.REQUIRED_RULE_IDS
        ]
        total_evaluable = len(evaluable_rules)
        compliance_score = round(passed_count / total_evaluable, 2) if total_evaluable > 0 else 0.0

        # Gate COMPLIANT: must have score >= 0.8 AND all required rules must strictly PASS
        required_rule_results = [r for r in rule_results if r["rule_id"] in self.REQUIRED_RULE_IDS]
        all_required_passed = all(r["status"] == "PASSED" for r in required_rule_results)

        if compliance_score >= 0.8 and all_required_passed:
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