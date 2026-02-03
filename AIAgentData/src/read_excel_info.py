import pandas as pd
import json
import os

# Update path to the correct file
excel_path = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\06_11新车辆仿真模型信息.xlsx"

if not os.path.exists(excel_path):
    print(f"File not found: {excel_path}")
    exit(1)

try:
    df = pd.read_excel(excel_path)
    print("Columns:", df.columns.tolist())
    print("-" * 20)
    # print(json.dumps(df.to_dict(orient='records'), ensure_ascii=False, indent=2, default=str))
    for i, row in df.iterrows():
        print(f"{i}: {row['文本']}")
except Exception as e:
    print(f"Error reading Excel: {e}")
