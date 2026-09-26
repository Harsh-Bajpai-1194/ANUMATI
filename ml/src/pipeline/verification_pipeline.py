import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Union, Any

from src.config import REPORT_FOLDER
from src.preprocessing.pdf_reader import PDFReader
from src.ocr.ocr_engine import OCREngine
from src.rules.aicte_rules import AICTERuleEngine

logger = logging.getLogger("anumati-ml.verification_pipeline")


class VerificationPipeline:
    """
    End-to-End Rule-Based Verification Pipeline for Institutional Documents.
    Executes deterministic checks across the full document flow:
    1. Ingestion, integrity validation, and metadata extraction (PDFReader)
    2. Hybrid text extraction and image conversion (OCREngine)
    3. Statutory AICTE compliance and missing disclosure flagging (AICTERuleEngine)
    4. Structured JSON report generation (saved to outputs/reports/)
    """

    def __init__(
        self,
        target_academic_year: Optional[str] = None,
        min_words_threshold: int = 15,
        dpi: int = 300,
    ):
        self.ocr_engine = OCREngine(min_words_threshold=min_words_threshold, dpi=dpi)
        self.rule_engine = AICTERuleEngine(target_academic_year=target_academic_year)

    def verify_document(
        self,
        source: Union[str, Path, bytes],
        document_name: Optional[str] = None,
        save_report: bool = True,
        save_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute full deterministic verification.

        Parameters:
            source: File path, Path object, or raw in-memory bytes.
            document_name: Optional filename for in-memory byte streams.
            save_report: Whether to write JSON report to outputs/reports/.
            save_images: Whether to render high-res page images to outputs/images/.

        Returns:
            Dict containing the consolidated verification report.
        """
        # Phase 1: Ingestion & Document Diagnostics
        reader = PDFReader(source, document_name=document_name)
        metadata = reader.get_metadata()
        dimensions = reader.get_page_dimensions()
        doc_stem = reader.document_stem

        # Optional: Render images if explicitly requested
        saved_images = []
        if save_images:
            try:
                saved_images = [str(p) for p in reader.extract_images()]
            except Exception as exc:
                logger.warning(f"Image rendering skipped: {exc}")

        # Phase 2: Hybrid Text Extraction (Digital layer + OCR fallback)
        extraction_result = self.ocr_engine.process_document(
            reader,
            save_text_file=True
        )

        # Phase 3: Deterministic Statutory AICTE Compliance & Disclosure Evaluation
        compliance_result = self.rule_engine.evaluate_text(extraction_result["full_text"])

        # Phase 4: Consolidate Verification Report
        report: Dict[str, Any] = {
            "document": {
                "name": reader.document_name,
                "stem": doc_stem,
                "total_pages": reader.total_pages(),
                "file_size_bytes": metadata.get("file_size_bytes", 0),
                "is_encrypted": metadata.get("is_encrypted", False),
                "format": metadata.get("format", "PDF"),
                "page_dimensions": dimensions,
                "rendered_images": saved_images,
            },
            "text_extraction": {
                "method": extraction_result["extraction_method"],
                "ocr_available": extraction_result["ocr_engine_available"],
                "total_words": extraction_result["total_words"],
                "total_characters": extraction_result["total_characters"],
                "text_file_path": extraction_result["text_file_path"],
                "page_breakdown": [
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

        # Save structured JSON verification report to outputs/reports/<doc_stem>_verification.json
        report_path = None
        if save_report:
            REPORT_FOLDER.mkdir(parents=True, exist_ok=True)
            report_path = REPORT_FOLDER / f"{doc_stem}_verification.json"
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            report["verification_metadata"]["report_file_path"] = str(report_path)
            logger.info(f"Saved verification report to: {report_path}")

        return report