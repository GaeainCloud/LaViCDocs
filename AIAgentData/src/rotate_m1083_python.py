from logger import get_logger
log = get_logger(__name__)
from config import DOWNLOADS_DIR
from utils.glb_utils import rotate_glb_y180

model_path = DOWNLOADS_DIR / "M1083_A1P2_Truck_AI_Rodin.glb"

if not model_path.exists():
    log.info(f"Error: File not found at {model_path}")
    raise SystemExit(1)

log.info(f"Loading {model_path}...")
rotate_glb_y180(model_path, model_path)
log.info("Done.")
