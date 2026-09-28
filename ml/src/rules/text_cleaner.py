import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("anumati-ml.text_cleaner")


class TextCleaner:
    """
    Cleans raw text extracted from PDFs and OCR, and extracts
    structured institutional entities using regular expressions.
    """

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """
        Normalize text:
        - Fixes broken lower-case words across line breaks while preserving compound hyphens
        - Normalizes unicode quotes, hyphens, and whitespace
        - Consolidates redundant whitespace and excessive newlines
        """
        if not raw_text:
            return ""

        text = raw_text

        # 1. Normalize line wraps:
        # Lowercase broken words (insti-\ntution -> institution)
        text = re.sub(r"([a-z]{2,})-\s*\n\s*([a-z]{2,})", r"\1\2", text)
        # Preserved compound terms (Anti-\nRagging -> Anti-Ragging, 2024-\n25 -> 2024-25)
        text = re.sub(r"([A-Za-z0-9]+)-\s*\n\s*([A-Za-z0-9]+)", r"\1-\2", text)

        # 2. Normalize standard quotes and dashes
        text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
        text = text.replace("—", "-").replace("–", "-")

        # 3. Strip non-printable / control characters while preserving standard ASCII and newlines
        text = re.sub(r"[^\x20-\x7E\n\t]", " ", text)

        # 4. Consolidate whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)

        return text.strip()

    @staticmethod
    def extract_entities(text: str) -> Dict[str, Any]:
        """
        Extract structured entities relevant to AICTE approval verification.
        """
        cleaned = TextCleaner.clean_text(text)

        # 1. Strict AICTE Institute ID (Requires explicit identifier label)
        institute_id_match = re.search(
            r"\b(?:AICTE\s*(?:Permanent\s*)?ID|Permanent\s*Institute\s*ID|Institute\s*ID|PID)[:\s#]*([1-9]-\d{8,12})\b",
            cleaned,
            re.IGNORECASE,
        )

        # 2. Academic Year (e.g. 2024-25, 2024-2025)
        academic_year_match = re.search(
            r"\b(20\d{2}[-–/](?:20)?\d{2})\b",
            cleaned
        )

        # 3. Application Number
        application_id_match = re.search(
            r"\b(?:Application\s*ID|Application\s*No\.?|App\s*No\.?)[:\s#]*([1-9]-\d{8,12})\b",
            cleaned,
            re.IGNORECASE,
        )

        # 4. Contact Information
        emails = list(set(re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", cleaned)))
        phones = list(set(re.findall(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b", cleaned)))

        # 5. Student-to-Faculty Ratio (SFR) mentions (e.g. 1:15, 1:20, 20:1, 30:1)
        sfr_match = re.search(
            r"\b(?:SFR|Student\s*Faculty\s*Ratio|Student\s*to\s*Faculty\s*Ratio)[:\s]*(\d+\s*[:/]\s*\d+)\b",
            cleaned,
            re.IGNORECASE,
        )

        # 6. Land Area (Acres, Hectares, Sq. Meters, sq m, sqm)
        land_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(Acres?|Hectares?|Sq\.?\s*Meters?|Square\s*Meters?|Sq\.?\s*m\.?|sqm)\b",
            cleaned,
            re.IGNORECASE,
        )

        # 7. Total Faculty Count
        faculty_count_match = re.search(
            r"\b(?:Total\s*Faculty|Faculty\s*Count|Number\s*of\s*Faculty)[:\s]*(\d+)\b",
            cleaned,
            re.IGNORECASE,
        )

        clean_sfr = sfr_match.group(1).replace(" ", "") if sfr_match else None

        return {
            "institute_id": institute_id_match.group(1) if institute_id_match else None,
            "academic_year": academic_year_match.group(1) if academic_year_match else None,
            "application_id": application_id_match.group(1) if application_id_match else None,
            "sfr_ratio": clean_sfr,
            "land_area": f"{land_match.group(1)} {land_match.group(2)}" if land_match else None,
            "land_value": float(land_match.group(1)) if land_match else None,
            "land_unit": land_match.group(2).lower() if land_match else None,
            "total_faculty": int(faculty_count_match.group(1)) if faculty_count_match else None,
            "emails": emails,
            "phones": phones,
            "has_aicte_mention": bool(re.search(r"\baicte|all\s+india\s+council\b", cleaned, re.IGNORECASE)),
            "word_count": len(cleaned.split()),
        }