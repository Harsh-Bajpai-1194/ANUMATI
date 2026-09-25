import argparse
from pathlib import Path
from src.preprocessing.pdf_reader import PDFReader, PDFProcessingError
from src.config import UPLOAD_FOLDER


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract images and metadata from a PDF using PDFReader."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        default="college.pdf",
        help="PDF filename in uploads folder or full path",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Resolution in DPI for page rendering (default: 300)",
    )
    parser.add_argument(
        "--pages",
        nargs="+",
        type=int,
        default=None,
        help="Specific page indices (0-indexed) to convert (e.g. --pages 0 1)",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Display document metadata and page geometry",
    )
    return parser.parse_args()


def resolve_pdf_path(pdf_arg: str) -> Path:
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
        print(f"Error: {exc}")
        return 1

    try:
        reader = PDFReader(pdf_path)

        print("=" * 40)
        print(" ANUMATI PDF INGESTION & CONVERSION")
        print("=" * 40)
        print(f"Document : {pdf_path.name}")
        print(f"Pages    : {reader.total_pages()}")

        if args.info:
            print("\n--- Metadata ---")
            for k, v in reader.get_metadata().items():
                print(f"  {k:16}: {v}")

            print("\n--- Page Dimensions ---")
            for p in reader.get_page_dimensions():
                print(f"  Page {p['page_number']}: {p['width']} x {p['height']} pt ({p['orientation']})")

        print(f"\nRendering images (DPI: {args.dpi})...")
        images = reader.extract_images(dpi=args.dpi, pages=args.pages)

        print(f"Successfully generated {len(images)} image(s):")
        for i, img in enumerate(images, start=1):
            print(f"  {i}. {img}")

        print("\nCompleted Successfully.")
        return 0

    except PDFProcessingError as err:
        print(f"PDF Processing Error: {err}")
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())