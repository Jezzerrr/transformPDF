from pathlib import Path


def ensure_parent_folder(file_path):
    """
    Create a folder if it doesn't exist yet.
    This function is not yet in use.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
