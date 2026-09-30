import io
import json
import logging
import os
import secrets
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile
import asyncio

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.config import UPLOAD_FOLDER

from src.pipeline.verification_pipeline import VerificationPipeline
from src.classification.document_classifier import DocumentClassifier
from src.signature.signature_detector import SignatureDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("anumati-ml")

# Internal Shared Secret Authentication (Issue #83, CodeRabbit CWE-1392)
ENVIRONMENT = os.getenv("ENV", os.getenv("ENVIRONMENT", os.getenv("NODE_ENV", ""))).lower()
IS_EXPLICIT_DEV = ENVIRONMENT in ("development", "dev", "local", "test")

ML_INTERNAL_TOKEN = os.getenv("ML_INTERNAL_TOKEN")
if not ML_INTERNAL_TOKEN:
    if IS_EXPLICIT_DEV:
        ML_INTERNAL_TOKEN = "dev-secret-internal-token-change-in-production"
    else:
        raise RuntimeError(
            "FATAL: ML_INTERNAL_TOKEN must be explicitly configured when not running in development mode!"
        )

if not IS_EXPLICIT_DEV and ML_INTERNAL_TOKEN == "dev-secret-internal-token-change-in-production":
    raise RuntimeError(
        "FATAL: ML_INTERNAL_TOKEN cannot use the default secret in non-development environments!"
    )

if not ML_INTERNAL_TOKEN.isascii():
    raise RuntimeError("FATAL: ML_INTERNAL_TOKEN must contain only ASCII characters.")

app = FastAPI(
    title="ANUMATI ML & Document Evaluation Microservice",
    version="1.2.0",
    description="Microservice for document classification, OCR extraction, AICTE compliance verification, and signature detection."
)

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

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  
MAX_PAGES = 100

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
    if len(doc_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES / (1024 * 1024):.1f}MB"
        )

    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
            
        doc = fitz.open(stream=doc_bytes, filetype="pdf")
        total_pages = len(doc)
        doc.close()
        
        if total_pages > MAX_PAGES:
            raise HTTPException(
                status_code=413,
                detail=f"Document exceeds maximum allowed pages ({MAX_PAGES}). Found {total_pages} pages."
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupted PDF document.")

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
            save_images=False  
        )
    except Exception as exc:
        logger.error(f"Verification pipeline failed: {exc}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to process PDF.") from exc

    full_text = (
        report.get("text_extraction", {}).get("full_text")
        or report.get("extracted_entities", {}).get("clean_text")
        or ""
    )

    classification_result = document_classifier.classify_text(full_text)
    signature_result = signature_detector.detect_signatures_in_pdf(doc_bytes)

    flags: List[Dict[str, str]] = []
    comp_eval = report["compliance_evaluation"]

    for rule in comp_eval.get("rules", []):
        if rule["status"] in ["FAILED", "WARNING"]:
            flags.append({
                "ruleCode": rule["rule_id"],
                "description": rule["details"],
                "severity": rule["severity"]
            })

    if not signature_result.get("signature_detected"):
        flags.append({
            "ruleCode": "MISSING_SIGNATURE",
            "description": "No institutional authorization signatures detected on scanned pages.",
            "severity": "medium"
        })

    if not signature_result.get("stamp_detected"):
        flags.append({
            "ruleCode": "MISSING_OFFICIAL_SEAL",
            "description": "No colored official seal or institutional rubber stamp detected.",
            "severity": "low"
        })

    is_flagged = any(f["severity"] in ["high", "critical"] for f in flags) or comp_eval["overall_status"] == "NON_COMPLIANT"

    return {
        "success": True,
        "document": report["document"],
        "classification": classification_result,
        "textExtraction": {
            "ocrConfidenceScore": report["text_extraction"].get("ocr_confidence"),
            "method": report["text_extraction"]["method"],
            "totalWords": report["text_extraction"]["total_words"],
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
        "complianceScore": round(comp_eval["compliance_score"], 2),
        "anomalyDetection": {
            "flagged": is_flagged,
            "flags": flags
        },
        "rawModelResponse": report
    }


def _read_file_sync(target_path: Path) -> bytes:
    with open(target_path, "rb") as f:
        return f.read()


@app.post("/evaluate")
async def evaluate_document(
    request: Request,
    file: Optional[UploadFile] = File(None),
    filename: Optional[str] = Form(None),
    filePath: Optional[str] = Form(None),
    targetAcademicYear: Optional[str] = Form(None),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token")
):
    # Constant-time comparison & ASCII check to prevent timing attacks and 500s (Issue #83, CodeRabbit)
    if (
        not x_internal_token
        or not x_internal_token.isascii()
        or not secrets.compare_digest(x_internal_token, ML_INTERNAL_TOKEN)
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing or invalid X-Internal-Token header."
        )

    ALLOWED_ROOTS = [
        UPLOAD_FOLDER.resolve(),
        (UPLOAD_FOLDER.parent.parent / "backend" / "uploads").resolve(),
        (UPLOAD_FOLDER.parent.parent / "uploads").resolve(),
    ]
    
    def check_safe_path(target: Path):
        normalized_target = target.resolve(strict=False)
        if not any(normalized_target.is_relative_to(root) for root in ALLOWED_ROOTS):
            raise HTTPException(
                status_code=403, 
                detail="Security Error: Path is outside allowed directories."
            )

    def build_safe_target_path(path_str: str) -> Path:
        if not path_str:
            raise HTTPException(status_code=400, detail="'filePath' must be a non-empty string.")
        target = Path(path_str).resolve(strict=False)
        check_safe_path(target)
        return target

    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
            target_path_str = data.get("filePath")
            target_path = build_safe_target_path(target_path_str)
            
            if not target_path.exists() or not target_path.is_file():
                raise HTTPException(status_code=404, detail="File not found.")

            doc_bytes = await asyncio.to_thread(_read_file_sync, target_path)
            target_year = data.get("targetAcademicYear")
            
            return await asyncio.to_thread(execute_evaluation, doc_bytes, target_path.name, target_year)

        if file is not None:
            doc_bytes = await file.read()
            return await asyncio.to_thread(execute_evaluation, doc_bytes, file.filename or "uploaded.pdf", targetAcademicYear)

        if filePath:
            target_path = build_safe_target_path(filePath)
            
            if not target_path.exists() or not target_path.is_file():
                raise HTTPException(status_code=404, detail="File not found.")
                
            doc_bytes = await asyncio.to_thread(_read_file_sync, target_path)
            
            return await asyncio.to_thread(execute_evaluation, doc_bytes, target_path.name, targetAcademicYear)

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
    