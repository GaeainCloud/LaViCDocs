from logger import get_logger
log = get_logger(__name__)
import pandas as pd

from config import MODELS_DIR

excel_path = MODELS_DIR / "16_21新舰载机仿真模型信息.xlsx"

try:
    df = pd.read_excel(excel_path)
    log.info("Model Names in Excel:")
    for name in df["文本"]:
        log.info(f"'{name}'")
except Exception as e:
    log.info(f"Error reading excel: {e}")
