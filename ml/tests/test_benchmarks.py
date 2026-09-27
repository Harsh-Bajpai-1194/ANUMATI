"""
Unit tests for ML benchmark metrics, stress testing, and model optimization cache.
"""

import pytest
from PIL import Image
from src.benchmark.metrics import (
    levenshtein_distance,
    calculate_cer,
    calculate_wer,
    calculate_accuracy
)
from src.benchmark.stress_tester import StressTester
from src.optimization.model_optimizer import DocumentPageCache, ModelOptimizer
from src.benchmark.benchmarker import PipelineBenchmarker


def test_levenshtein_distance():
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("AICTE", "AICTE") == 0
    assert levenshtein_distance("AICTE", "ACTE") == 1  # Deletion


def test_cer_and_wer_metrics():
    ref = "All India Council for Technical Education"
    hyp_exact = "All India Council for Technical Education"
    hyp_typo = "All India Council for Technical Educaton"  # 1 char deletion

    # Exact match
    assert calculate_cer(ref, hyp_exact) == 0.0
    assert calculate_wer(ref, hyp_exact) == 0.0
    assert calculate_accuracy(ref, hyp_exact) == 100.0

    # Slight typo
    cer = calculate_cer(ref, hyp_typo)
    assert 0.0 < cer < 0.1
    wer = calculate_wer(ref, hyp_typo)
    assert wer == 1 / 6  # 1 word out of 6 has an error


def test_stress_tester_transformations():
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))

    # Test skew
    skewed = StressTester.simulate_skew(img, angle_degrees=15.0)
    assert skewed.size[0] >= img.size[0]

    # Test low resolution downsampling
    low_res = StressTester.simulate_low_resolution(img, scale_factor=0.5)
    assert low_res.size == img.size

    # Test blur
    blurred = StressTester.simulate_blur(img, radius=1.0)
    assert blurred.size == img.size

    # Test composite degradation
    all_distorted = StressTester.apply_all_distortions(img)
    assert all_distorted is not None


def test_document_page_cache():
    cache = DocumentPageCache(max_entries=2)
    sample_data = b"page-image-bytes-data"
    key1 = cache.compute_hash(sample_data)

    # Initial miss
    assert cache.get(key1) is None
    assert cache.stats()["misses"] == 1

    # Insert and hit
    cache.set(key1, {"text": "AICTE Handbook", "confidence": 0.95})
    cached_val = cache.get(key1)
    assert cached_val is not None
    assert cached_val["text"] == "AICTE Handbook"
    assert cache.stats()["hits"] == 1

    # LRU eviction test
    key2 = "hash2"
    key3 = "hash3"
    cache.set(key2, {"page": 2})
    cache.set(key3, {"page": 3})  # key1 should be evicted now
    assert cache.get(key1) is None


def test_model_optimizer_quantization_profile():
    profile = ModelOptimizer.get_quantization_profile()
    assert "pytorch_fp32" in profile
    assert "onnx_int8" in profile
    assert profile["onnx_int8"]["size_mb"] < profile["pytorch_fp32"]["size_mb"]


def test_benchmarker_accuracy_suite():
    benchmarker = PipelineBenchmarker()
    report = benchmarker.generate_full_report()
    assert "accuracy_metrics" in report
    assert "optimization_profile" in report
    assert report["accuracy_metrics"]["preprocessor_resilience_confirmed"] is True