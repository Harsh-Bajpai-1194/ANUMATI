import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure 'ml' directory is in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.pipeline.verification_pipeline import VerificationPipeline
from src.classification.document_classifier import DocumentClassifier
from src.signature.signature_detector import SignatureDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("anumati-ml")

app = FastAPI(
    title="ANUMATI ML & Document Evaluation Microservice",
    version="1.2.0",
    description="Microservice for document classification, OCR extraction, AICTE compliance verification, and signature detection."
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5000",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
MAX_PAGES = 100

# Initialize Pipelines and Classifiers
verification_pipeline = VerificationPipeline()
document_classifier = DocumentClassifier()
signature_detector = SignatureDetector()


class EvaluationRequest(BaseModel):
    filePath: Optional[str] = None
    documentId: Optional[str] = None
    targetAcademicYear: Optional[str] = None


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ANUMATI ML Microservice",
        "version": "1.2.0",
        "pipeline_ready": True
    }


def execute_evaluation(
    doc_bytes: bytes,
    filename: str,
    target_academic_year: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes end-to-end evaluation using all underlying engines.
    """
    if len(doc_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES / (1024 * 1024):.1f}MB"
        )

    # 1. Run Verification Pipeline (PDFReader, OCR, AICTE Rules)
    pipeline = (
        VerificationPipeline(target_academic_year=target_academic_year)
        if target_academic_year
        else verification_pipeline
    )

    try:
        report = pipeline.verify_document(
            doc_bytes,
            document_name=filename,
            save_report=True,
            save_images=True
        )
    except Exception as exc:
        logger.error(f"Verification pipeline failed: {exc}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to process PDF: {exc}")

    full_text = report["extracted_entities"].get("clean_text") or ""
    # Retrieve raw text if not directly in entities
    text_path = report["text_extraction"].get("text_file_path")
    if text_path and Path(text_path).exists():
        full_text = Path(text_path).read_text(encoding="utf-8")

    # 2. Run Document Classifier
    classification_result = document_classifier.classify_text(full_text)

    # 3. Run Signature and Stamp Detector
    signature_result = signature_detector.detect_signatures_in_pdf(doc_bytes)

    # 4. Map rule outcomes & checks to Anomaly Flags (for MongoDB AiEvaluation model)
    flags: List[Dict[str, str]] = []
    comp_eval = report["compliance_evaluation"]

    # Rule failures mapped to anomaly flags
    for rule in comp_eval.get("rules", []):
        if rule["status"] in ["FAILED", "WARNING"]:
            flags.append({
                "ruleCode": rule["rule_id"],
                "description": rule["details"],
                "severity": rule["severity"]
            })

    # Missing signature flag
    if not signature_result.get("signature_detected"):
        flags.append({
            "ruleCode": "MISSING_SIGNATURE",
            "description": "No institutional authorization signatures detected on scanned pages.",
            "severity": "medium"
        })

    # Missing official seal flag
    if not signature_result.get("stamp_detected"):
        flags.append({
            "ruleCode": "MISSING_OFFICIAL_SEAL",
            "description": "No colored official seal or institutional rubber stamp detected.",
            "severity": "low"
        })

    is_flagged = any(f["severity"] in ["high", "critical"] for f in flags) or comp_eval["overall_status"] == "NON_COMPLIANT"

    # Compute extraction quality heuristic
    word_count = report["text_extraction"]["total_words"]
    if word_count > 50:
        extraction_score = 0.95
    elif word_count > 10:
        extraction_score = 0.80
    else:
        extraction_score = 0.30

    # 5. Return standardized payload compatible with Backend & MongoDB
    return {
        "success": True,
        "document": report["document"],
        "classification": classification_result,
        "textExtraction": {
            "extractionQualityScore": extraction_score,
            "method": report["text_extraction"]["method"],
            "totalWords": word_count,
            "extractedEntities": report["extracted_entities"]
        },
        "signatureVerification": {
            "detected": signature_result["signature_detected"],
            "stampDetected": signature_result["stamp_detected"],
            "confidenceScore": signature_result["confidence"],
            "status": signature_result["status"],
            "pageDetections": signature_result["page_detections"]
        },
        "complianceEvaluation": comp_eval,
        "anomalyDetection": {
            "flagged": is_flagged,
            "confidence": round(comp_eval["compliance_score"], 2),
            "flags": flags
        },
        "rawModelResponse": report
    }


@app.post("/evaluate")
async def evaluate_document(
    request: Request,
    file: Optional[UploadFile] = File(None),
    filename: Optional[str] = Form(None),
    filePath: Optional[str] = Form(None)
):
    """
    Accepts document evaluation requests via:
    1. JSON body: { "filePath": "...", "documentId": "..." } (Used by Node.js backend)
    2. Multipart file upload: file (Used by frontend direct uploads)
    """
    try:
        # Check if request has application/json content-type
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
            target_path_str = data.get("filePath")
            if not target_path_str:
                raise HTTPException(status_code=400, detail="'filePath' field is required in JSON body.")

            target_path = Path(target_path_str).resolve()
            if not target_path.exists():
                raise HTTPException(status_code=404, detail=f"File not found at: {target_path}")

            with open(target_path, "rb") as f:
                doc_bytes = f.read()

            target_year = data.get("targetAcademicYear")
            return execute_evaluation(doc_bytes, target_path.name, target_year)

        # Multipart upload: direct file
        if file is not None:
            doc_bytes = await file.read()
            return execute_evaluation(doc_bytes, file.filename or "uploaded.pdf")

        # Multipart form: filePath field
        if filePath:
            target_path = Path(filePath).resolve()
            if not target_path.exists():
                raise HTTPException(status_code=404, detail=f"File not found at: {target_path}")
            with open(target_path, "rb") as f:
                doc_bytes = f.read()
            return execute_evaluation(doc_bytes, target_path.name)

        raise HTTPException(
            status_code=400,
            detail="Either a 'file' upload or a valid 'filePath' in JSON body must be provided."
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Internal evaluation error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while evaluating the document."
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)