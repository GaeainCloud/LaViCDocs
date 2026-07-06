from logger import get_logger
log = get_logger(__name__)
import shutil
from pathlib import Path

from config import MODELS_DIR
from utils.package_utils import create_flat_zip

model = "Su-33_Flanker-D"
src_png = MODELS_DIR / "downloads" / f"{model}.png"
dst_dir = MODELS_DIR / model / model
dst_png = dst_dir / f"{model}.png"

if src_png.exists():
    dst_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Copying {src_png} to {dst_png}")
    shutil.copy(src_png, dst_png)
else:
    log.info(f"Source image not found: {src_png}")

model_root = MODELS_DIR / model
zip_path = MODELS_DIR / f"{model}.zip"
create_flat_zip(model_root, zip_path)
log.info("Done.")
