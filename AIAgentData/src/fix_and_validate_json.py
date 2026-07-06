from config import MODELS_DIR
from logger import get_logger
from utils.package_utils import validate_package

log = get_logger(__name__)

PACKAGES = [
    "J-20_Mighty_Dragon",
    "F-22_Raptor",
    "F-35_Lightning_II",
    "Su-57_Felon",
]


def fix_and_validate():
    for pkg_name in PACKAGES:
        zip_path = MODELS_DIR / f"{pkg_name}.zip"
        passed, errors = validate_package(zip_path)
        if passed:
            log.info(f"{pkg_name}: validation passed")
        else:
            log.warning(f"{pkg_name}: validation failed")
            for err in errors:
                log.warning(f"  - {err}")


if __name__ == "__main__":
    fix_and_validate()
