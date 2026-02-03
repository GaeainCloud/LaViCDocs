import pandas as pd
import json
import os
import sys
import uuid
import random
import time

# Add current directory to path to import validator
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from validator import validate_agent_data

def generate_agent_key():
    """Generate a unique agent key."""
    # Format similar to existing key: AGENTKEY_ + digits
    timestamp = int(time.time() * 1000)
    random_part = random.randint(100000, 999999)
    return f"AGENTKEY_{timestamp}{random_part}"

def clean_filename(name):
    """Clean string to be safe for filename."""
    return "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()

def main():
    base_dir = os.path.dirname(current_dir)
    excel_path = os.path.join(base_dir, "models", "新evtol仿真模型信息.xlsx")
    template_path = os.path.join(base_dir, "examples", "03evtolAgent.json")
    output_dir = os.path.join(base_dir, "models")
    schema_path = os.path.join(base_dir, "src", "校验代码参考", "AgentData_schema.json")

    print(f"Reading Excel from: {excel_path}")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Failed to read Excel: {e}")
        return

    print(f"Reading Template from: {template_path}")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
            # Template is a list, take the first item as the base agent
            base_agent = template_data[0]
    except Exception as e:
        print(f"Failed to read Template: {e}")
        return

    print(f"Found {len(df)} models in Excel.")
    
    generated_files = []

    for index, row in df.iterrows():
        # Create a deep copy of the base agent
        new_agent = json.loads(json.dumps(base_agent))
        
        # Extract data from Excel
        name = row.get("文本", f"Unknown_Agent_{index}")
        desc_attrs = row.get("基本属性", "")
        desc_sensors = row.get("感知能力", "")
        desc_comms = row.get("通信能力", "")
        desc_type = row.get("类型", "")
        
        # Construct Description
        full_desc = f"类型: {desc_type}\n基本属性: {desc_attrs}\n感知能力: {desc_sensors}\n通信能力: {desc_comms}"
        
        # Update Agent Fields
        new_agent["agentKey"] = generate_agent_key()
        new_agent["agentName"] = name
        new_agent["agentNameI18n"] = name
        new_agent["agentDesc"] = full_desc
        
        # Generate a simple keyword (pinyin or english placeholder)
        # For now, using a safe version of the name or existing keyword + index
        new_agent["agentKeyword"] = f"evtol_{index + 1}"

        # Wrap in list as per Schema requirement (AgentData is a list of agents)
        agent_data = [new_agent]
        
        # Define output filename
        safe_name = clean_filename(name)
        file_name = f"{safe_name}.json"
        file_path = os.path.join(output_dir, file_name)
        
        # Save JSON
        print(f"Generating {file_name}...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(agent_data, f, ensure_ascii=False, indent=2)
        
        # Validate
        print(f"Validating {file_name}...")
        if validate_agent_data(schema_path, file_path):
            print(f"SUCCESS: {file_name} generated and validated.")
            generated_files.append(file_path)
        else:
            print(f"FAILURE: {file_name} failed validation.")
    
    print("-" * 30)
    print(f"Total Generated & Validated: {len(generated_files)}")
    print("Files saved to:", output_dir)

if __name__ == "__main__":
    main()
