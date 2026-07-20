from pathlib import Path


def file_exists(file_path):
    return Path(file_path).exists()


def create_folder(folder_path):
    """Create a folder if it doesn't already exist."""
    Path(folder_path).mkdir(parents=True, exist_ok=True)


def get_file_name(file_path):
    """Return filename without extension."""
    return Path(file_path).stem


def get_extension(file_path):
    """Return the file extension."""
    return Path(file_path).suffix


def get_file_name_with_extension(file_path):
    """Return filename with extension."""
    return Path(file_path).name


def delete_file(file_path):
    """Delete a file if it exists."""
    file = Path(file_path)

    if file.exists():
        file.unlink()