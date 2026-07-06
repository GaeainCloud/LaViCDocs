import os
import subprocess
from pathlib import Path

from config import MODELS_DIR
from logger import get_logger
from utils.package_utils import fix_agent_json_paths

log = get_logger(__name__)


def fix_agent_json(models_dir=None):
    models_dir = Path(models_dir) if models_dir else MODELS_DIR

    try:
        items = os.listdir(models_dir)
    except FileNotFoundError:
        log.error(f"Directory not found: {models_dir}")
        return

    dirs = [d for d in items if (models_dir / d).is_dir() and d not in ("assets", "downloads")]

    log.info(f"Found directories to process: {dirs}")

    for model_name in dirs:
        json_path = models_dir / model_name / "agent.json"
        if not json_path.exists():
            log.warning(f"{json_path} not found. Skipping.")
            continue

        fix_agent_json_paths(json_path, model_name)


if __name__ == "__main__":
    log.info("Starting agent.json fix...")
    fix_agent_json()

    log.info("Starting re-zipping...")
    zip_script = Path(__file__).parent / "zip_models.py"
    subprocess.run(["python", str(zip_script)], cwd=str(MODELS_DIR.parent))
