import shutil

from config import MODELS_DIR, GLB_ROTATION_MARKER
from logger import get_logger
from utils.glb_utils import rotate_glb_to_yup
from utils.package_utils import create_flat_zip

log = get_logger(__name__)

VEHICLES = [
    "M1083_A1P2_Truck",
    "Dongfeng_Mengshi_CSK181",
    "Norinco_Lynx_CS_VP4",
    "Oshkosh_JLTV",
    "Polaris_MRZR_Alpha",
]


def process_and_package(model_name):
    log.info(f"Processing {model_name}...")

    model_root = MODELS_DIR / model_name
    inner_dir = model_root / model_name
    glb_path = inner_dir / f"{model_name}_AI_Rodin.glb"

    # 尝试从 downloads 恢复原始模型
    download_path = MODELS_DIR / "downloads" / f"{model_name}_AI_Rodin.glb"
    if download_path.exists():
        inner_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(download_path, glb_path)
        marker = glb_path.with_name(f"{glb_path.name}{GLB_ROTATION_MARKER}")
        if marker.exists():
            marker.unlink()
            log.info(f"  Removed stale rotation marker: {marker}")
        log.info(f"  Restored raw model from {download_path}")

    if not glb_path.exists():
        log.error(f"  Error: Model file not found for {model_name}")
        return

    rotate_glb_to_yup(glb_path, glb_path)

    agent_json_path = model_root / "agent.json"
    if not agent_json_path.exists():
        log.error(f"  Error: agent.json not found at {agent_json_path}")
        return

    zip_path = MODELS_DIR / f"{model_name}.zip"
    create_flat_zip(model_root, zip_path)
    log.info(f"  Packaging complete: {zip_path}")


if __name__ == "__main__":
    for vehicle in VEHICLES:
        process_and_package(vehicle)
    log.info("All tasks finished.")
