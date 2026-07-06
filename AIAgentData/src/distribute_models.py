from logger import get_logger
log = get_logger(__name__)
import shutil

from config import MODELS_DIR

base_dir = MODELS_DIR
downloads_dir = base_dir / "downloads"

models = [
    "Dongfeng_Mengshi_CSK181",
    "Dongfeng-15_Missile_Launcher",
    "M1083_A1P2_Truck",
    "Norinco_Lynx_CS_VP4",
    "Oshkosh_JLTV",
    "Polaris_MRZR_Alpha",
]

for model in models:
    src_glb = downloads_dir / f"{model}_AI_Rodin.glb"
    dest_dir = base_dir / model / model
    dest_glb = dest_dir / f"{model}_AI_Rodin.glb"

    if src_glb.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Moving {src_glb} -> {dest_glb}")
        shutil.copy2(src_glb, dest_glb)
    else:
        log.info(f"Source not found: {src_glb}")

    src_png = downloads_dir / f"{model}.png"
    dest_png = dest_dir / f"{model}.png"
    if src_png.exists():
        log.info(f"Copying {src_png} -> {dest_png}")
        shutil.copy2(src_png, dest_png)
    else:
        log.info(f"PNG Source not found: {src_png}")
