import pandas as pd
import os

excel_path = os.path.join(r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models", "16_21新舰载机仿真模型信息.xlsx")

try:
    df = pd.read_excel(excel_path)
    print("Columns:", df.columns.tolist())
    print("First few rows:")
    print(df.head())
    
    # Extract names and descriptions for further use
    for index, row in df.iterrows():
        print(f"Row {index}: {row.to_dict()}")
        
except Exception as e:
    print(f"Error reading excel: {e}")
