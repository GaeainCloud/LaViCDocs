from logger import get_logger
log = get_logger(__name__)
import json
import pandas as pd

from config import MODELS_DIR

excel_path = MODELS_DIR / "新evtol仿真模型信息.xlsx"

try:
    df = pd.read_excel(excel_path)
    log.info("Columns:", df.columns.tolist())
    log.info("-" * 20)
    log.info(json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2, default=str))
except Exception as e:
    log.info(f"Error reading Excel: {e}")
