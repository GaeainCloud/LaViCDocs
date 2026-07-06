import os
from pathlib import Path

from config import MODELS_DIR
from logger import get_logger
from utils.package_utils import validate_package

log = get_logger(__name__)


def deep_check(models_dir=None, packages=None):
    """验收检查所有或指定的模型包。

    Args:
        models_dir: 模型目录，默认使用 config.MODELS_DIR
        packages: 要检查的包名列表，默认自动发现所有 .zip 文件
    """
    models_dir = Path(models_dir) if models_dir else MODELS_DIR

    if packages is None:
        packages = [p.stem for p in models_dir.glob("*.zip")]

    if not packages:
        log.warning(f"No ZIP packages found in {models_dir}")
        return

    log.info(f"Checking {len(packages)} packages...")

    passed = 0
    failed = 0

    for pkg_name in packages:
        zip_path = models_dir / f"{pkg_name}.zip"
        ok, errors = validate_package(zip_path)
        if ok:
            passed += 1
        else:
            failed += 1

    log.info(f"\nResults: {passed} passed, {failed} failed out of {len(packages)} packages.")


if __name__ == "__main__":
    deep_check()
