from pathlib import Path
import argparse
from src.preprocessing.pdf_reader import PDFReader
from src.config import UPLOAD_FOLDER


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract images from a PDF using PDFReader."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        default="college.pdf",
        help="PDF filename in uploads folder or full path",
    )
    return parser.parse_args()


def resolve_pdf_path(pdf_arg):
    pdf_path = Path(pdf_arg)
    if not pdf_path.is_absolute():
        pdf_path = UPLOAD_FOLDER / pdf_arg
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")
    return pdf_path


def main():
    args = parse_args()
    try:
        pdf_path = resolve_pdf_path(args.pdf)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    reader = PDFReader(pdf_path)

    print(...)
    print("PDF PROCESSING")
    print(...)
    print("Pages :", reader.total_pages())
    print()

    images = reader.extract_images()
    print("\nImages Generated:")

    for i, image in enumerate(images, start=1):
        print(f"{i}. {image}")
    
    print()
    print("Completed Successfully")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
