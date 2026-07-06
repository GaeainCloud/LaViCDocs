from logger import get_logger
log = get_logger(__name__)
import pandas as pd

from config import MODELS_DIR

excel_path = MODELS_DIR / "16_21新舰载机仿真模型信息.xlsx"

try:
    df = pd.read_excel(excel_path)
    log.info("Columns:", df.columns.tolist())
    log.info("First few rows:")
    log.info(df.head())
    for index, row in df.iterrows():
        log.info(f"Row {index}: {row.to_dict()}")
except Exception as e:
    log.info(f"Error reading excel: {e}")
