import fitz
from pathlib import Path

from src.config import IMAGE_FOLDER


class PDFReader:
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)

    def open_pdf(self):
        """Open and return the PDF document."""
        return fitz.open(self.pdf_path)

    def total_pages(self):
        """Return the total number of pages in the PDF."""
        with self.open_pdf() as pdf:
            return len(pdf)

    def extract_text(self):
        """Extract text from all pages of the PDF."""
        with self.open_pdf() as pdf:
            text = []

            for page in pdf:
                text.append(page.get_text())

        return "\n".join(text)

    def extract_images(self, dpi=300):
        """
        Convert each PDF page to an image.

        Parameters:
            dpi (int): Image resolution. Default = 300.

        Returns:
            list[Path]: Paths of all saved images.
        """

        saved_images = []

        with self.open_pdf() as pdf:

            for index, page in enumerate(pdf, start=1):

                image_path = IMAGE_FOLDER / f"page_{index}.png"

                pix = page.get_pixmap(dpi=dpi)

                pix.save(image_path)

                saved_images.append(image_path)

        return saved_images