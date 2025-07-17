import os
from datetime import datetime
from pathlib import Path

def get_filename_from_url(url):
    """Extract the filename from a Dropbox URL."""
    return url.split("/")[-1].split("?")[0]

def get_absolute_path(filename):
    """Return the full absolute path to a file in the current directory."""
    return str(Path.cwd() / filename)

def create_output_folder():
    """Ensure output folder exists."""
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    return output_dir

def timestamped_filename(base, ext):
    """Create a filename like base_20250701_143200.ext"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{timestamp}.{ext}"

def cleanup_temp_files(*file_paths):
    """Delete specified files if they exist."""
    for path in file_paths:
        try:
            os.remove(path)
            print(f"🧹 Removed: {path}")
        except FileNotFoundError:
            pass