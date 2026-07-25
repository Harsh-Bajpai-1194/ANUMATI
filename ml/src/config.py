from pathlib import Path

# Project Directories

# ml/
BASE_DIR = Path(__file__).resolve().parent.parent

# Input Folder
UPLOAD_FOLDER = BASE_DIR / "uploads"

# Output Folders
OUTPUT_FOLDER = BASE_DIR / "outputs"
IMAGE_FOLDER = OUTPUT_FOLDER / "images"
TEXT_FOLDER = OUTPUT_FOLDER / "text"
REPORT_FOLDER = OUTPUT_FOLDER / "reports"

# Create Required Folders
for folder in [
    UPLOAD_FOLDER,
    OUTPUT_FOLDER,
    IMAGE_FOLDER,
    TEXT_FOLDER,
    REPORT_FOLDER,
]:
    folder.mkdir(parents=True, exist_ok=True)