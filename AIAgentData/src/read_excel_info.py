from logger import get_logger
log = get_logger(__name__)
import pandas as pd

from config import MODELS_DIR

excel_path = MODELS_DIR / "06_11新车辆仿真模型信息.xlsx"

if not excel_path.exists():
    log.info(f"File not found: {excel_path}")
    raise SystemExit(1)

try:
    df = pd.read_excel(excel_path)
    log.info("Columns:", df.columns.tolist())
    log.info("-" * 20)
    for i, row in df.iterrows():
        log.info(f"{i}: {row['文本']}")
except Exception as e:
    log.info(f"Error reading Excel: {e}")
