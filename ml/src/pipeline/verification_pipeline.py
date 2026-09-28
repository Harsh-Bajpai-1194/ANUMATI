"""
End-to-End Statutory AICTE Document Verification Pipeline.
Orchestrates:
1. PDF Ingestion & Preprocessing
2. Digital Layer & OCR Text Extraction
3. Rule-Based Compliance Evaluation & Scoring
4. Comprehensive Structured Verification Report Generation
"""

import json
import logging
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Union

from src.preprocessing.pdf_reader import PDFReader
from src.ocr.ocr_engine import OCREngine
from src.rules.aicte_rules import AICTERuleEngine
from src.config import REPORT_FOLDER

logger = logging.getLogger("anumati-ml.verification_pipeline")


class VerificationPipeline:
    """
    Automated document compliance verification pipeline for AICTE Approval Process.
    """

    def __init__(
        self,
        target_academic_year: Optional[str] = None,
        min_words_threshold: int = 15,
        dpi: int = 300,
        image_format: str = "png",
    ):
        self.target_academic_year = target_academic_year
        self.dpi = dpi
        self.image_format = image_format
        self.ocr_engine = OCREngine(min_words_threshold=min_words_threshold, dpi=dpi)
        self.rule_engine = AICTERuleEngine(target_academic_year=target_academic_year)

    def verify_document(
        self,
        reader_or_source: Union[PDFReader, str, Path, bytes],
        document_name: Optional[str] = None,
        save_report: bool = True,
        save_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute full verification pipeline on a document.
        """
        if isinstance(reader_or_source, PDFReader):
            reader = reader_or_source
        else:
            reader = PDFReader(reader_or_source, document_name=document_name)

        doc_stem = reader.document_stem
        logger.info(f"Initiating statutory verification for document: {reader.document_name}")

        # 1. Page Conversion (optional preview extraction)
        saved_images = []
        if save_images:
            try:
                saved_images = [
                    str(p)
                    for p in reader.extract_images(
                        dpi=self.dpi,
                        image_format=self.image_format,
                    )
                ]
            except Exception as exc:
                logger.warning(f"Failed to save page images during verification: {exc}")

        # 2. Text Extraction (Digital layer + OCR fallback)
        extraction_result = self.ocr_engine.process_document(
            reader,
            save_text_file=save_report,
        )

        full_extracted_text = extraction_result["full_text"]

        # 3. Rule Evaluation & Statutory Compliance Scoring
        compliance_result = self.rule_engine.evaluate_text(full_extracted_text)

        # 4. Synthesize Final Verification Report
        report: Dict[str, Any] = {
            "document": {
                "name": reader.document_name,
                "total_pages": extraction_result["total_pages"],
                "file_size_bytes": reader.get_metadata().get("file_size_bytes", 0),
                "is_encrypted": reader.get_metadata().get("is_encrypted", False),
            },
            "text_extraction": {
                "method": extraction_result["extraction_method"],
                "total_words": extraction_result["total_words"],
                "total_characters": extraction_result["total_characters"],
                "ocr_engine_available": extraction_result["ocr_engine_available"],
                "text_file_path": extraction_result.get("text_file_path"),
                "pages_preview": [
                    {
                        "page_number": p["page_number"],
                        "word_count": p["word_count"],
                        "method": p["method"],
                    }
                    for p in extraction_result["pages"]
                ],
            },
            "compliance_evaluation": {
                "overall_status": compliance_result["overall_status"],
                "compliance_score": compliance_result["compliance_score"],
                "total_rules": compliance_result["total_rules_evaluated"],
                "passed_rules": compliance_result["passed_rules"],
                "rules": compliance_result["rules"],
            },
            "extracted_entities": compliance_result["extracted_entities"],
            "verification_metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pipeline_version": "1.0.0",
                "engine": "ANUMATI_Rule_Pipeline",
            },
        }

        # 5. Save structured JSON verification report
        report_path = None
        if save_report:
            REPORT_FOLDER.mkdir(parents=True, exist_ok=True)

            # Prevent overwriting when distinct documents share the same basename
            if reader.pdf_path:
                doc_id = hashlib.sha256(str(reader.pdf_path.resolve()).encode("utf-8")).hexdigest()[:8]
            elif reader.stream_bytes:
                doc_id = hashlib.sha256(reader.stream_bytes).hexdigest()[:8]
            else:
                doc_id = None

            report_filename = f"{doc_stem}_{doc_id}_verification.json" if doc_id else f"{doc_stem}_verification.json"
            report_path = REPORT_FOLDER / report_filename

            # Include report_file_path in metadata before writing so saved JSON contains it
            report["verification_metadata"]["report_file_path"] = str(report_path)
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.info(f"Saved verification report to: {report_path}")

        return report
    