"""
Comprehensive ML Pipeline Benchmarking Suite.
Measures latency per page, extraction throughput, peak memory usage,
and OCR accuracy across digital and scanned PDF pipelines.
"""

import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw

from src.preprocessing.pdf_reader import PDFReader
from src.ocr.image_preprocessor import ImagePreprocessor
from .metrics import calculate_wer, calculate_cer, calculate_accuracy
from .stress_tester import StressTester
from src.optimization.model_optimizer import DocumentPageCache, ModelOptimizer

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    PYTESSERACT_AVAILABLE = False


class PipelineBenchmarker:
    """Runs automated benchmarks for the ANUMATI ML document pipeline."""

    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.page_cache = DocumentPageCache(max_entries=128)

    def benchmark_digital_extraction(self, pdf_path: str, max_pages: int = 15) -> Dict[str, Any]:
        """Measures digital text extraction latency and peak memory on a PDF."""
        tracemalloc.start()
        start_time = time.perf_counter()

        reader = PDFReader(pdf_path)
        total_pages = min(reader.total_pages(), max_pages)

        extracted_characters = 0
        total_words = 0

        with reader.open_pdf() as pdf:
            for page_idx in range(total_pages):
                text = pdf[page_idx].get_text()
                extracted_characters += len(text)
                total_words += len(text.split())

        duration = time.perf_counter() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        latency_per_page_ms = (duration / total_pages * 1000) if total_pages > 0 else 0.0
        throughput = (total_pages / duration) if duration > 0 else 0.0

        return {
            "file": Path(pdf_path).name,
            "pages_benchmarked": total_pages,
            "total_time_seconds": round(duration, 3),
            "latency_per_page_ms": round(latency_per_page_ms, 2),
            "throughput_pages_per_sec": round(throughput, 2),
            "total_words": total_words,
            "total_characters": extracted_characters,
            "peak_memory_mb": round(peak_mem / (1024 * 1024), 2)
        }

    def benchmark_ocr_accuracy_and_resilience(
        self,
        ground_truth: str = "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION\nAPPROVAL PROCESS HANDBOOK 2024-2025"
    ) -> Dict[str, Any]:
        """
        Benchmarks OCR accuracy and preprocessor noise resilience.
        Tests CER and WER under baseline and degraded conditions.
        """

        # 1. Generate a synthetic crisp document image
        img = Image.new("RGB", (900, 350), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((30, 30), ground_truth, fill=(0, 0, 0))

        # 2. Pristine Preprocessing
        processed_clean = self.preprocessor.preprocess(img, apply_binarization=False)

        # 3. Degraded / Stress condition: skewed (10 deg) + downsampled (60%)
        distorted_img = StressTester.simulate_skew(img, angle_degrees=10.0)
        distorted_img = StressTester.simulate_low_resolution(distorted_img, scale_factor=0.6)
        processed_restored = self.preprocessor.preprocess(distorted_img, apply_binarization=False)

        # 4. OCR Execution — fail closed if pytesseract or binary is unavailable
        if not PYTESSERACT_AVAILABLE or pytesseract is None:
            return {
                "ocr_status": "unavailable",
                "clean_benchmark": None,
                "stressed_benchmark": None,
                "preprocessor_resilience_confirmed": False
            }

        try:
            extracted_clean = pytesseract.image_to_string(processed_clean).strip()
            extracted_restored = pytesseract.image_to_string(processed_restored).strip()
        except Exception as exc:
            return {
                "ocr_status": f"error: {exc}",
                "clean_benchmark": None,
                "stressed_benchmark": None,
                "preprocessor_resilience_confirmed": False
            }

        if not extracted_clean or not extracted_restored:
            return {
                "ocr_status": "empty_ocr_result",
                "clean_benchmark": None,
                "stressed_benchmark": None,
                "preprocessor_resilience_confirmed": False
            }

        # 5. Metrics calculation
        cer_clean = calculate_cer(ground_truth, extracted_clean)
        wer_clean = calculate_wer(ground_truth, extracted_clean)
        acc_clean = calculate_accuracy(ground_truth, extracted_clean)

        cer_stress = calculate_cer(ground_truth, extracted_restored)
        wer_stress = calculate_wer(ground_truth, extracted_restored)
        acc_stress = calculate_accuracy(ground_truth, extracted_restored)

        resilience_confirmed = bool(acc_stress >= 70.0 and cer_stress <= 0.30)

        return {
            "ocr_status": "available",
            "clean_benchmark": {
                "cer": round(cer_clean, 4),
                "wer": round(wer_clean, 4),
                "character_accuracy_pct": round(acc_clean, 2)
            },
            "stressed_benchmark": {
                "distortion": "Skew (10°) + Downsampling (60%)",
                "cer": round(cer_stress, 4),
                "wer": round(wer_stress, 4),
                "character_accuracy_pct": round(acc_stress, 2)
            },
            "preprocessor_resilience_confirmed": resilience_confirmed
        }

    def generate_full_report(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """Runs the entire test suite and packages all benchmark metrics."""
        tesseract_ver = "Tesseract (unavailable)"
        if PYTESSERACT_AVAILABLE and pytesseract is not None:
            try:
                tesseract_ver = f"Tesseract {pytesseract.get_tesseract_version()}"
            except Exception:
                tesseract_ver = "Tesseract (binary missing)"

        results: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "environment": {
                "python_version": sys.version.split()[0],
                "ocr_engine": tesseract_ver,
                "pdf_engine": "PyMuPDF (fitz)",
                "acceleration": "INT8 Dynamic Quantization + Image Preprocessing"
            }
        }

        results["accuracy_metrics"] = self.benchmark_ocr_accuracy_and_resilience()

        if pdf_path and os.path.exists(pdf_path):
            results["pdf_performance"] = self.benchmark_digital_extraction(pdf_path, max_pages=15)

        results["optimization_profile"] = ModelOptimizer.get_quantization_profile()

        return results