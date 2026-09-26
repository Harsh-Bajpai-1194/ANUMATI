# Model Architecture Evaluation: Document Classification & Signature Detection

## 1. Overview
Institutional compliance forms (e.g., AICTE approval letters, faculty lists, land affidavits) have rigorous spatial structures and multi-modal signals (typed text, vector lines, handwritten signatures, and colored rubber stamps). This document evaluates deep learning architectures for production scaling.

---

## 2. Document Classification Architecture: LayoutLM vs TF-IDF / CNN

| Criteria | TF-IDF / Heuristic (Current) | Text CNN / Bi-LSTM | LayoutLMv3 (Evaluated) |
|---|---|---|---|
| **Latency** | **< 15 ms** | ~50 ms | ~350 ms (CPU) / ~40 ms (GPU) |
| **Compute / Weight Size** | **< 1 MB** | ~15 MB | ~500 MB |
| **Spatial Awareness** | None (pure text tokens) | None | **Full 2D Bounding Box coordinates** |
| **Form Robustness** | Moderate (keyword dependent) | High | **Superior (reads tables & key-value grids)** |

### Recommendation for Scaling:
- **Phase 1 (Lightweight / Edge)**: The current `DocumentClassifier` provides deterministic classification with zero heavy GPU memory overhead.
- **Phase 2 (Deep Learning)**: Fine-tune **LayoutLMv3-base** on synthetic and institutional datasets using token coordinates extracted by `PDFReader.get_page_dimensions()`. LayoutLMv3 jointly encodes text tokens, 2D coordinates, and image patches.

---

## 3. Signature & Stamp Detection Architecture

| Method | Color/Vector Segmentation (Current) | MobileNetV3 / TensorFlow CNN | YOLOv8-Doc / Faster R-CNN |
|---|---|---|---|
| **Stamp Detection** | **High precision for blue/purple/red ink** | Moderate | High |
| **Signature Strokes** | Vector cluster heuristics | Region classification | **Full bounding box regression** |
| **Deployment Complexity** | **Zero C++ binary / 0 MB weights** | ~20 MB (TFLite) | ~40 MB (ONNX / PyTorch) |

### Recommendation for Scaling:
- The hybrid approach combines pixel-color ink density with PyMuPDF drawing paths.
- For bounding box localization, train a lightweight **YOLOv8-nano** or **TensorFlow Lite MobileNet SSD** model on Kaggle Tobacco3482 or open signature datasets.