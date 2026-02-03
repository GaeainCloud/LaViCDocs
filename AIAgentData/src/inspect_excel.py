import pandas as pd
import json

excel_path = r"d:\AIProduct\GAEALaViC\AIAgentData\models\新evtol仿真模型信息.xlsx"

try:
    df = pd.read_excel(excel_path)
    print("Columns:", df.columns.tolist())
    print("-" * 20)
    # Convert to list of dicts and print as JSON for clarity
    print(json.dumps(df.to_dict(orient='records'), ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(f"Error reading Excel: {e}")
