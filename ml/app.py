from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import re

from src.preprocessing.pdf_reader import PDFReader

app = FastAPI(
    title="ANUMATI ML & Document Evaluation Service",
    version="1.0.0",
    description="Microservice for extracting text, validating signatures, and running anomaly checks on institutional PDFs."
)

# Enable CORS for local backend/frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EvaluationRequest(BaseModel):
    filePath: str


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ANUMATI ML Service"}


@app.post("/evaluate")
def evaluate_document(payload: EvaluationRequest):
    pdf_path = Path(payload.filePath)

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Document file not found at: {payload.filePath}"
        )

    try:
        reader = PDFReader(pdf_path)
        total_pages = reader.total_pages()
        raw_text = reader.extract_text()

        # 1. Basic Metadata / Entity Extraction
        clean_text = raw_text.strip()
        word_count = len(clean_text.split())

        # Simple pattern matching for common institutional terms
        extracted_entities = {
            "totalWords": word_count,
            "hasAicteMention": bool(re.search(r"aicte|all india council", raw_text, re.IGNORECASE)),
            "hasDate": bool(re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", raw_text)),
            "detectedEmails": re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text),
            "previewSnippet": clean_text[:300] if clean_text else ""
        }

        # 2. Heuristic Anomaly Detection
        flags = []
        if total_pages == 0:
            flags.append({
                "ruleCode": "EMPTY_DOCUMENT",
                "description": "The uploaded PDF has 0 pages.",
                "severity": "critical"
            })
        elif word_count < 10:
            flags.append({
                "ruleCode": "LOW_TEXT_CONTENT",
                "description": "Very low text density detected. Document might be a scanned image without OCR.",
                "severity": "medium"
            })

        anomaly_detection = {
            "flagged": len(flags) > 0,
            "confidence": 0.95 if len(flags) == 0 else 0.70,
            "flags": flags
        }

        # 3. Overall OCR score
        ocr_confidence_score = 0.92 if word_count > 20 else 0.50

        return {
            "success": True,
            "document": {
                "filename": pdf_path.name,
                "totalPages": total_pages,
            },
            "extractedTextMetadata": {
                "ocrConfidenceScore": ocr_confidence_score,
                "extractedEntities": extracted_entities
            },
            "anomalyDetection": anomaly_detection,
            "rawModelResponse": {
                "status": "processed",
                "engine": "PyMuPDF_v1"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error evaluating document: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)