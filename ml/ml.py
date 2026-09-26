import argparse
import logging
from pathlib import Path

from src.preprocessing.pdf_reader import PDFReader, PDFProcessingError
from src.pipeline.verification_pipeline import VerificationPipeline
from src.config import UPLOAD_FOLDER

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("anumati-ml.cli")


def parse_args():
    parser = argparse.ArgumentParser(
        description="ANUMATI ML Document Ingestion, OCR & Verification Pipeline."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        default="college.pdf",
        help="PDF filename in uploads folder or full path",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Execute complete end-to-end AICTE verification pipeline",
    )
    parser.add_argument(
        "--year",
        default=None,
        help="Target academic year to verify against (e.g. 2024-25)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Resolution in DPI for page rendering (default: 300)",
    )
    parser.add_argument(
        "--format",
        default="png",
        help="Output image format (png, jpeg, jpg). Default: png",
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
        logger.error(str(exc))
        return 1

    try:
        # Full End-to-End Verification Pipeline Mode
        if args.verify:
            print("=" * 60)
            print(" ANUMATI END-TO-END DOCUMENT VERIFICATION PIPELINE")
            print("=" * 60)
            print(f"Target Document : {pdf_path.name}")

            pipeline = VerificationPipeline(target_academic_year=args.year, dpi=args.dpi)
            report = pipeline.verify_document(pdf_path, save_report=True, save_images=True)

            comp = report["compliance_evaluation"]
            doc = report["document"]
            txt = report["text_extraction"]
            entities = report["extracted_entities"]

            print(f"Total Pages     : {doc['total_pages']}")
            print(f"Text Extraction : {txt['method']} ({txt['total_words']} words)")
            print(f"Report File     : {report['verification_metadata'].get('report_file_path')}")
            print("\n--- Extracted Entities ---")
            print(f"  AICTE Institute ID : {entities.get('institute_id') or 'NOT DETECTED'}")
            print(f"  Academic Year      : {entities.get('academic_year') or 'NOT DETECTED'}")
            print(f"  Land Area          : {entities.get('land_area') or 'NOT DETECTED'}")
            print(f"  Student-Faculty    : {entities.get('sfr_ratio') or 'NOT DETECTED'}")

            print("\n--- AICTE Compliance Verdict ---")
            print(f"  VERDICT : {comp['overall_status']}")
            print(f"  SCORE   : {int(comp['compliance_score'] * 100)}% ({comp['passed_rules']}/{comp['total_rules']} rules passed)")
            print("\n--- Rule Evaluation Details ---")
            for r in comp["rules"]:
                status_icon = "✓" if r["status"] == "PASSED" else ("⚠" if r["status"] == "WARNING" else "✗")
                print(f"  [{status_icon}] {r['rule_id']} ({r['status']}): {r['details']}")

            print("\n" + "=" * 60)
            return 0

        # Standard Preprocessing Mode
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

        images = reader.extract_images(dpi=args.dpi, image_format=args.format)
        print(f"\nSuccessfully generated {len(images)} image(s).")
        return 0

    except PDFProcessingError as err:
        logger.error(f"PDF Processing Error: {err}")
        return 1
    except Exception:
        logger.exception("Unexpected failure while running verification pipeline")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())