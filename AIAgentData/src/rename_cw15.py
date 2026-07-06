from pathlib import Path

from config import MODELS_DIR
from logger import get_logger

log = get_logger(__name__)

OLD_NAME = "纵横CW-15"
NEW_NAME = "纵横CW-15无人机"


def rename_cw15(base_dir: Path = MODELS_DIR):
    base_dir = Path(base_dir)
    old_path = base_dir / OLD_NAME
    new_path = base_dir / NEW_NAME

    if not old_path.exists():
        log.info(f"Directory {old_path} not found. checking if already renamed.")
        if new_path.exists():
            log.info(f"Directory {new_path} already exists.")
        return

    log.info(f"Renaming {old_path} to {new_path}")
    old_path.rename(new_path)

    # Rename subfolder
    old_sub = new_path / OLD_NAME
    new_sub = new_path / NEW_NAME
    if old_sub.exists():
        log.info(f"Renaming subfolder {old_sub} to {new_sub}")
        old_sub.rename(new_sub)

        # Rename files inside
        for file_path in new_sub.iterdir():
            filename = file_path.name
            if filename.startswith(OLD_NAME) and not filename.startswith(NEW_NAME):
                new_filename = filename.replace(OLD_NAME, NEW_NAME, 1)
                new_file_path = new_sub / new_filename
                log.info(f"Renaming file {filename} to {new_filename}")
                file_path.rename(new_file_path)

    # Remove old zip if exists
    old_zip = base_dir / f"{OLD_NAME}.zip"
    if old_zip.exists():
        old_zip.unlink()
        log.info(f"Removed old zip {old_zip}")


if __name__ == "__main__":
    rename_cw15()
