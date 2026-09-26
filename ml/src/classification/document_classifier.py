import re
import logging
from typing import Dict, List, Tuple, Any

logger = logging.getLogger("anumati-ml.document_classifier")


class DocumentClassifier:
    """
    Classifies institutional documents into standard regulatory categories:
    - AICTE_APPROVAL_LETTER
    - FACULTY_LIST
    - LAND_DOCUMENT
    - AFFIDAVIT
    - OTHER
    """

    CATEGORIES = {
        "AICTE_APPROVAL_LETTER": {
            "keywords": [
                "aicte", "all india council for technical education", "approval process handbook",
                "extension of approval", "permanent institute id", "application id",
                "sanctioned intake", "approved intake", "academic year"
            ],
            "weight": 1.2,
        },
        "FACULTY_LIST": {
            "keywords": [
                "faculty", "teaching staff", "professor", "associate professor",
                "assistant professor", "designation", "qualification", "department",
                "date of joining", "pay scale", "pan number", "sfr"
            ],
            "weight": 1.1,
        },
        "LAND_DOCUMENT": {
            "keywords": [
                "land area", "khasra", "survey number", "acres", "hectares",
                "built-up area", "instructional area", "administrative area",
                "deed", "ownership", "sub-registrar", "demarcation"
            ],
            "weight": 1.1,
        },
        "AFFIDAVIT": {
            "keywords": [
                "affidavit", "notary", "oath", "solemnly affirm", "deponent",
                "verified at", "stamp paper", "non-judicial", "declaration"
            ],
            "weight": 1.3,
        },
    }

    def __init__(self, min_confidence_threshold: float = 0.35):
        self.min_confidence_threshold = min_confidence_threshold

    def classify_text(self, text: str) -> Dict[str, Any]:
        """
        Classifies input text and returns predicted category, confidence score,
        and matched keyword signals.
        """
        if not text or not text.strip():
            return {
                "category": "OTHER",
                "confidence": 0.0,
                "scores": {},
                "matched_signals": [],
                "description": "Empty document text; unable to classify.",
            }

        text_lower = text.lower()
        category_scores: Dict[str, float] = {}
        matched_by_cat: Dict[str, List[str]] = {}

        for cat_name, cat_data in self.CATEGORIES.items():
            matches = []
            score = 0.0
            for kw in cat_data["keywords"]:
                # Count occurrences using word boundary where possible
                count = len(re.findall(r"\b" + re.escape(kw) + r"\b", text_lower))
                if count > 0:
                    matches.append(kw)
                    score += min(count, 5) * cat_data["weight"]

            category_scores[cat_name] = score
            matched_by_cat[cat_name] = matches

        total_score = sum(category_scores.values())

        if total_score == 0:
            return {
                "category": "OTHER",
                "confidence": 0.10,
                "scores": category_scores,
                "matched_signals": [],
                "description": "No definitive institutional classification keywords matched.",
            }

        # Find category with highest weighted score
        best_cat, best_score = max(category_scores.items(), key=lambda item: item[1])
        confidence = round(best_score / total_score, 2)

        # Apply confidence threshold
        final_category = best_cat if confidence >= self.min_confidence_threshold else "OTHER"

        return {
            "category": final_category,
            "confidence": confidence,
            "scores": {k: round(v, 2) for k, v in category_scores.items()},
            "matched_signals": matched_by_cat.get(best_cat, []),
            "description": f"Classified as '{final_category}' with {int(confidence * 100)}% confidence.",
        }