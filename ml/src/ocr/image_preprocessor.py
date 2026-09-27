import logging
from pathlib import Path
from typing import Optional, Union
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger("anumati-ml.image_preprocessor")


class ImagePreprocessor:
    """
    Image enhancement and cleaning pipeline to maximize OCR recognition accuracy.
    Performs grayscale conversion, contrast enhancement, edge sharpening, and optional binarization.
    """

    def __init__(
        self,
        contrast_factor: float = 1.8,
        binarize_threshold: int = 180,
    ):
        """
        Parameters:
            contrast_factor (float): Multiplier for contrast enhancement. 1.8 is chosen
                to separate faded stamp ink and low-contrast text from paper backgrounds.
            binarize_threshold (int): Grayscale cutoff (0-255). Values > threshold become white (255),
                others become black (0). Default 180 separates dark ink from off-white scans.
        """
        self.contrast_factor = contrast_factor
        self.binarize_threshold = binarize_threshold

    def preprocess(
        self,
        image_source: Union[str, Path, Image.Image],
        output_path: Optional[Union[str, Path]] = None,
        apply_binarization: bool = False,
    ) -> Image.Image:
        """
        Enhance an image for OCR.

        Parameters:
            image_source: Path to an image file or an existing PIL Image.
            output_path: Optional path to save the preprocessed image.
            apply_binarization: Whether to apply hard 1-bit thresholding.
                Default is False because Tesseract's internal adaptive thresholding
                often yields higher accuracy on grayscale images with uneven lighting.

        Returns:
            PIL.Image: Preprocessed image in grayscale ('L') or binary ('1') mode.
        """
        if isinstance(image_source, (str, Path)):
            img = Image.open(str(image_source))
        elif isinstance(image_source, Image.Image):
            # Explicit copy guarantees caller's original image instance is never modified
            img = image_source.copy()
        else:
            raise TypeError(f"Unsupported image source type: {type(image_source)}")

        # 1. Convert to Grayscale ('L' creates a new image instance)
        gray_img = img.convert("L")

        # 2. Enhance contrast
        enhancer = ImageEnhance.Contrast(gray_img)
        enhanced_img = enhancer.enhance(self.contrast_factor)

        # 3. Sharpen edges to improve character definition
        sharpened_img = enhanced_img.filter(ImageFilter.SHARPEN)

        # 4. Optional Binarization (Thresholding)
        if apply_binarization:
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