import logging
from pathlib import Path
from typing import Optional, Union
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger("anumati-ml.image_preprocessor")


class ImagePreprocessor:
    """
    Image enhancement and cleaning pipeline to maximize OCR recognition accuracy.
    Performs grayscale conversion, contrast enhancement, noise filtering, and binarization.
    """

    def __init__(self, contrast_factor: float = 1.8, binarize_threshold: int = 180):
        self.contrast_factor = contrast_factor
        self.binarize_threshold = binarize_threshold

    def preprocess(
        self,
        image_source: Union[str, Path, Image.Image],
        output_path: Optional[Union[str, Path]] = None,
        apply_binarization: bool = True
    ) -> Image.Image:
        """
        Enhance an image for OCR.

        Parameters:
            image_source: Path to an image file or an existing PIL Image.
            output_path: Optional path to save the preprocessed image.
            apply_binarization: Whether to apply black & white thresholding.

        Returns:
            PIL.Image: Preprocessed image in grayscale or binary mode.
        """
        if isinstance(image_source, (str, Path)):
            img = Image.open(str(image_source))
        elif isinstance(image_source, Image.Image):
            img = image_source.copy()
        else:
            raise TypeError(f"Unsupported image source type: {type(image_source)}")

        # 1. Convert to Grayscale
        gray_img = img.convert("L")

        # 2. Enhance contrast
        enhancer = ImageEnhance.Contrast(gray_img)
        enhanced_img = enhancer.enhance(self.contrast_factor)

        # 3. Sharpen edges to improve character definition
        sharpened_img = enhanced_img.filter(ImageFilter.SHARPEN)

        # 4. Optional Binarization (Thresholding)
        if apply_binarization:
            # Map pixels: > threshold -> 255 (white background), else 0 (black text)
            processed_img = sharpened_img.point(
                lambda p: 255 if p > self.binarize_threshold else 0,
                mode="1"
            )
        else:
            processed_img = sharpened_img

        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            processed_img.save(str(out_p))
            logger.debug(f"Saved preprocessed image to: {out_p}")

        return processed_img