import os
import zipfile
from pathlib import Path

from config import MODELS_DIR
from logger import get_logger

log = get_logger(__name__)

def zip_model_folders(models_dir=None):
    models_dir = Path(models_dir) if models_dir else MODELS_DIR

    try:
        items = os.listdir(models_dir)
    except FileNotFoundError:
        log.error(f"Directory not found: {models_dir}")
        return

    dirs = [d for d in items if (models_dir / d).is_dir() and d not in ("assets", "downloads")]

    log.info(f"Found directories to zip: {dirs}")

    for folder_name in dirs:
        folder_path = models_dir / folder_name
        zip_path = models_dir / f"{folder_name}.zip"

        log.info(f"Zipping {folder_name} to {zip_path}...")

        try:
            with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, str(folder_path))
                        zipf.write(file_path, arcname=rel_path)
            log.info(f"Successfully created {zip_path}")
        except Exception as e:
            log.error(f"Failed to zip {folder_name}: {e}")

if __name__ == "__main__":
    zip_model_folders()
