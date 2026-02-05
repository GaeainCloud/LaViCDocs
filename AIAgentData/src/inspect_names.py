import pandas as pd
import os

excel_path = os.path.join(r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models", "16_21新舰载机仿真模型信息.xlsx")

try:
    df = pd.read_excel(excel_path)
    print("Model Names in Excel:")
    for name in df['文本']:
        print(f"'{name}'")
except Exception as e:
    print(f"Error reading excel: {e}")
