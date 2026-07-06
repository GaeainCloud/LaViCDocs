from pathlib import Path

from config import MODELS_DIR, DOWNLOADS_DIR
from logger import get_logger
from utils.glb_utils import rotate_glb_to_yup

log = get_logger(__name__)

MODELS = [
    "J-20_Mighty_Dragon",
    "F-22_Raptor",
    "F-35_Lightning_II",
    "Su-57_Felon"
]

def main():
    for model_name in MODELS:
        src_path = DOWNLOADS_DIR / f"{model_name}_AI_Rodin.glb"
        dst_path = MODELS_DIR / model_name / model_name / f"{model_name}_AI_Rodin.glb"

        if not src_path.exists():
            log.warning(f"Source not found: {src_path}")
            if dst_path.exists():
                log.warning(f"  Fallback: Using existing target {dst_path}")
                src_path = dst_path
            else:
                log.warning(f"  Skipping {model_name}: No file found.")
                continue

        rotate_glb_to_yup(src_path, dst_path)

if __name__ == "__main__":
    main()
