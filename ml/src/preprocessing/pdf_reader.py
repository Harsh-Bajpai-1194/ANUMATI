import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Sequence

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from src.config import IMAGE_FOLDER

logger = logging.getLogger("anumati-ml.pdf_reader")

SUPPORTED_IMAGE_FORMATS = {"png", "jpeg", "jpg"}


class PDFProcessingError(Exception):
    """Base exception for PDF processing errors."""
    pass


class EncryptedPDFError(PDFProcessingError):
    """Raised when an encrypted/password-protected PDF cannot be opened."""
    pass


class CorruptedPDFError(PDFProcessingError):
    """Raised when the PDF file or byte stream is corrupted."""
    pass


class EmptyPDFError(PDFProcessingError):
    """Raised when the PDF has 0 pages."""
    pass


class PDFReader:
    """
    Robust PDF Ingestion and Image Conversion Pipeline.
    Supports file paths, Path objects, and in-memory byte streams.
    """

    def __init__(
        self,
        source: Union[str, Path, bytes, io.BytesIO],
        document_name: Optional[str] = None
    ):
        self.stream_bytes: Optional[bytes] = None
        self.pdf_path: Optional[Path] = None

        if isinstance(source, (str, Path)):
            self.pdf_path = Path(source)
            self.document_name = document_name or self.pdf_path.name
        elif isinstance(source, bytes):
            self.stream_bytes = source
            self.document_name = document_name or "document.pdf"
        elif isinstance(source, io.BytesIO):
            self.stream_bytes = source.getvalue()
            self.document_name = document_name or "document.pdf"
        else:
            raise TypeError(f"Unsupported source type: {type(source)}")

    @property
    def document_stem(self) -> str:
        """Returns document name without extension (used for output folders)."""
        return Path(self.document_name).stem

    def open_pdf(self) -> fitz.Document:
        """
        Open and return the PyMuPDF document instance.
        Validates encryption and integrity.
        """
        try:
            if self.pdf_path is not None:
                if not self.pdf_path.exists():
                    raise FileNotFoundError(f"PDF not found at: {self.pdf_path}")
                pdf = fitz.open(self.pdf_path)
            else:
                if not self.stream_bytes:
                    raise CorruptedPDFError("PDF byte stream is empty (0 bytes).")
                pdf = fitz.open(stream=self.stream_bytes, filetype="pdf")
        except FileNotFoundError:
            raise
        except Exception as exc:
            logger.error(f"Failed to open PDF '{self.document_name}': {exc}")
            raise CorruptedPDFError(f"Corrupted or invalid PDF document: {exc}") from exc

        if pdf.is_encrypted:
            # Try to authenticate with blank password
            if not pdf.authenticate(""):
                pdf.close()
                raise EncryptedPDFError(f"PDF '{self.document_name}' is password protected.")

        if len(pdf) == 0:
            pdf.close()
            raise EmptyPDFError(f"PDF '{self.document_name}' contains 0 pages.")

        return pdf

    def total_pages(self) -> int:
        """Return the total number of pages in the PDF."""
        with self.open_pdf() as pdf:
            return len(pdf)

    def get_metadata(self) -> Dict[str, Union[str, int, bool]]:
        """
        Extract document metadata, security info, and page count.
        """
        with self.open_pdf() as pdf:
            meta = pdf.metadata or {}
            file_size = (
                self.pdf_path.stat().st_size
                if self.pdf_path and self.pdf_path.exists()
                else len(self.stream_bytes or b"")
            )

            return {
                "document_name": self.document_name,
                "total_pages": len(pdf),
                "file_size_bytes": file_size,
                "is_encrypted": pdf.is_encrypted,
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "creator": meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
                "mod_date": meta.get("modDate", ""),
                "format": meta.get("format", ""),
            }

    def get_page_dimensions(self) -> List[Dict[str, float]]:
        """
        Retrieve page geometry (width, height, orientation) for each page.
        """
        dimensions = []
        with self.open_pdf() as pdf:
            for index, page in enumerate(pdf, start=1):
                rect = page.rect
                width = float(rect.width)
                height = float(rect.height)
                orientation = "landscape" if width > height else "portrait"
                dimensions.append({
                    "page_number": index,
                    "width": round(width, 2),
                    "height": round(height, 2),
                    "orientation": orientation,
                    "aspect_ratio": round(width / height, 3) if height > 0 else 0.0,
                })
        return dimensions

    def extract_text(self, pages: Optional[Sequence[int]] = None) -> str:
        """
        Extract text from all or specified pages (0-indexed).
        """
        with self.open_pdf() as pdf:
            selected_indices = pages if pages is not None else range(len(pdf))
            text_chunks = []
            for idx in selected_indices:
                if 0 <= idx < len(pdf):
                    text_chunks.append(pdf[idx].get_text())
            return "\n".join(text_chunks)

    def extract_images(
        self,
        output_dir: Optional[Path] = None,
        dpi: int = 300,
        image_format: str = "png",
        pages: Optional[Sequence[int]] = None
    ) -> List[Path]:
        """
        Convert PDF pages to image files.
        Images are saved in document-specific subfolders to prevent collisions.

        Parameters:
            output_dir (Optional[Path]): Destination folder. Defaults to IMAGE_FOLDER / <doc_stem>.
            dpi (int): Resolution DPI for rendering. Default is 300.
            image_format (str): Image extension, e.g. "png" or "jpeg". Default is "png".
            pages (Optional[Sequence[int]]): 0-indexed page list to render. Defaults to all.

        Returns:
            List[Path]: Paths of saved image files.
        """
        fmt = image_format.lower().lstrip(".")
        if fmt not in SUPPORTED_IMAGE_FORMATS:
            raise PDFProcessingError(
                f"Unsupported image format: '{image_format}'. Supported formats are: {', '.join(sorted(SUPPORTED_IMAGE_FORMATS))}"
            )

        target_dir = Path(output_dir) if output_dir else (IMAGE_FOLDER / self.document_stem)
        target_dir.mkdir(parents=True, exist_ok=True)

        saved_images = []

        with self.open_pdf() as pdf:
            selected_indices = list(pages) if pages is not None else list(range(len(pdf)))

            for page_idx in selected_indices:
                if page_idx < 0 or page_idx >= len(pdf):
                    logger.warning(
                        f"Skipping out-of-range page index {page_idx} for '{self.document_name}'"
                    )
                    continue

                page = pdf[page_idx]
                page_number = page_idx + 1
                image_path = target_dir / f"page_{page_number}.{fmt}"

                # Render page at specified resolution
                pix = page.get_pixmap(dpi=dpi)
                pix.save(str(image_path))
                saved_images.append(image_path)

        logger.info(
            f"Rendered {len(saved_images)} page image(s) for '{self.document_name}' in {target_dir}"
        )
        return saved_images