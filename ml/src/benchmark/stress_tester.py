"""
Stress-testing module to evaluate OCR resilience against degraded,
skewed, low-resolution, and noisy document scans.
"""

import math
from typing import Dict, Any, Tuple
from PIL import Image, ImageFilter, ImageOps
import numpy as np


class StressTester:
    """Simulates real-world scan degradations to test preprocessor robustness."""

    @staticmethod
    def simulate_skew(image: Image.Image, angle_degrees: float = 12.0) -> Image.Image:
        """Rotates the image by a given angle to simulate skewed scanning."""
        # Rotate with white background expansion
        return image.rotate(angle_degrees, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=(255, 255, 255))

    @staticmethod
    def simulate_low_resolution(image: Image.Image, scale_factor: float = 0.35) -> Image.Image:
        """
        Downsamples the image to simulate low DPI / compressed scans,
        then upscales it back to test interpolation artifacts.
        """
        w, h = image.size
        small_w = max(1, int(w * scale_factor))
        small_h = max(1, int(h * scale_factor))
        
        downsampled = image.resize((small_w, small_h), resample=Image.Resampling.NEAREST)
        return downsampled.resize((w, h), resample=Image.Resampling.BILINEAR)

    @staticmethod
    def simulate_blur(image: Image.Image, radius: float = 1.8) -> Image.Image:
        """Applies Gaussian blur to simulate out-of-focus mobile phone scans."""
        return image.filter(ImageFilter.GaussianBlur(radius=radius))

    @staticmethod
    def simulate_noise(image: Image.Image, noise_factor: float = 0.08) -> Image.Image:
        """Adds salt-and-pepper noise to simulate scanner sensor artifacting."""
        gray = image.convert("L")
        arr = np.array(gray, dtype=np.float32)
        noise = np.random.normal(0, noise_factor * 255, arr.shape)
        noisy_arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy_arr).convert("RGB")

    @classmethod
    def apply_all_distortions(cls, image: Image.Image) -> Image.Image:
        """Applies a composite stressful scenario: skewed + low-res + noisy + blurred."""
        img = cls.simulate_skew(image, angle_degrees=8.0)
        img = cls.simulate_low_resolution(img, scale_factor=0.5)
        img = cls.simulate_blur(img, radius=1.0)
        return img