import pandas as pd
import json
import os
import shutil
import uuid
import military_symbol
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import time

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
EXCEL_PATH = os.path.join(MODELS_DIR, "06_11新车辆仿真模型信息.xlsx")
TEMPLATE_JSON_PATH = os.path.join(PROJECT_ROOT, "examples", "01vehicleAgent.json")

# Source assets to copy (placeholders)
SOURCE_GLB_PLACEHOLDER = os.path.join(MODELS_DIR, "亿航EH216-S无人机", "亿航EH216-S无人机", "亿航EH216-S无人机_AI_Rodin.glb")
SOURCE_PNG_PLACEHOLDER = os.path.join(MODELS_DIR, "亿航EH216-S无人机", "亿航EH216-S无人机", "亿航EH216-S无人机.png")
DOWNLOADS_DIR = os.path.join(MODELS_DIR, "downloads")

# Model Mapping (Index in Excel -> English Name & Symbol Desc)
MODEL_MAPPING = {
    0: {"name": "Dongfeng-15_Missile_Launcher", "symbol_desc": "Friendly Missile Launcher"},
    1: {"name": "M1083_A1P2_Truck", "symbol_desc": "Friendly Cargo Truck"},
    2: {"name": "Polaris_MRZR_Alpha", "symbol_desc": "Friendly Armoured Fighting Vehicle"},
    3: {"name": "Oshkosh_JLTV", "symbol_desc": "Friendly Armoured Fighting Vehicle"},
    4: {"name": "Dongfeng_Mengshi_CSK181", "symbol_desc": "Friendly Armoured Fighting Vehicle"},
    5: {"name": "Norinco_Lynx_CS_VP4", "symbol_desc": "Friendly Armoured Fighting Vehicle"}
}

def generate_mil_symbol(name, desc, output_dir):
    print(f"Generating symbol for {name} ({desc})...")
    try:
        svg_string = military_symbol.get_symbol_svg_string_from_name(desc, style='light', bounding_padding=4, use_variants=True)
        if svg_string is None:
             print(f"  Warning: Could not generate SVG for '{desc}', falling back to 'Friendly Ground Vehicle'")
             svg_string = military_symbol.get_symbol_svg_string_from_name("Friendly Ground Vehicle", style='light', bounding_padding=4, use_variants=True)

        svg_filename = f"{name}_mil.svg"
        svg_path = os.path.join(output_dir, svg_filename)
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_string)
            
        png_filename = f"{name}_mil.png"
        png_path = os.path.join(output_dir, png_filename)
        
        drawing = svg2rlg(svg_path)
        renderPM.drawToFile(drawing, png_path, fmt="PNG")
        print(f"  Saved PNG to {png_path}")
        
        # Clean up SVG
        os.remove(svg_path)
        return png_filename
    except Exception as e:
        print(f"  Error generating symbol for {name}: {e}")
        return None

def main():
    if not os.path.exists(EXCEL_PATH):
        print(f"Excel file not found: {EXCEL_PATH}")
        return

    # Load Template
    with open(TEMPLATE_JSON_PATH, 'r', encoding='utf-8') as f:
        template_data = json.load(f)
        if isinstance(template_data, list):
            template_agent = template_data[0]
        else:
            template_agent = template_data

    # Load Excel
    df = pd.read_excel(EXCEL_PATH)

    for i, row in df.iterrows():
        if i not in MODEL_MAPPING:
            continue
        
        model_info = MODEL_MAPPING[i]
        en_name = model_info["name"]
        symbol_desc = model_info["symbol_desc"]
        cn_name = row['文本']
        description = str(row['基本属性']) + "\n类型: " + str(row['类型'])
        
        print(f"Processing {i}: {cn_name} -> {en_name}")

        # Create Directories
        model_dir = os.path.join(MODELS_DIR, en_name)
        assets_dir = os.path.join(model_dir, en_name)
        
        if os.path.exists(model_dir):
            shutil.rmtree(model_dir)
        os.makedirs(assets_dir)

        # Prepare Agent Data
        agent_data = template_data # Keep it as a list if the template is a list
        if isinstance(agent_data, list):
            current_agent = agent_data[0]
        else:
            current_agent = agent_data
            agent_data = [current_agent] # Ensure it's a list for final output if needed, but usually agent.json is a list

        # Update Fields
        current_agent['agentKey'] = f"AGENTKEY_{uuid.uuid4().int}"
        current_agent['agentName'] = en_name # Use English name for ID purposes or Display Name? Usually display name can be Chinese but folder name is English.
        # Let's keep agentName as English for safety in file paths, add i18n label if needed.
        # Actually, looking at 01vehicleAgent.json, agentName is "无人车辆（标准）".
        # So we can set agentName to Chinese name.
        current_agent['agentName'] = cn_name
        current_agent['agentNameI18n'] = cn_name
        current_agent['agentDesc'] = description
        
        # Paths (Placeholders, will be fixed by fix_and_zip_models.py later, but we set them relatively correct now)
        # Note: fix_and_zip_models.py expects us to put assets in {ModelName}/ folder
        # And set paths in json to something.
        
        # Assets filenames
        glb_name = f"{en_name}_AI_Rodin.glb"
        png_name = f"{en_name}.png"
        mil_name = f"{en_name}_mil.png"

        # Check for downloaded assets
        downloaded_glb = os.path.join(DOWNLOADS_DIR, f"{en_name}.glb")
        downloaded_png = os.path.join(DOWNLOADS_DIR, f"{en_name}.png")

        # Copy/Generate Assets
        # 1. GLB
        if os.path.exists(downloaded_glb):
            print(f"  Using downloaded GLB: {downloaded_glb}")
            shutil.copy(downloaded_glb, os.path.join(assets_dir, glb_name))
        elif os.path.exists(SOURCE_GLB_PLACEHOLDER):
            print(f"  Warning: Downloaded GLB not found, using placeholder.")
            shutil.copy(SOURCE_GLB_PLACEHOLDER, os.path.join(assets_dir, glb_name))
        else:
            print(f"  Warning: Source GLB not found at {SOURCE_GLB_PLACEHOLDER}")
            # Create dummy
            with open(os.path.join(assets_dir, glb_name), 'w') as f:
                f.write("dummy glb")

        # 2. Thumbnail PNG
        if os.path.exists(downloaded_png):
            print(f"  Using downloaded PNG: {downloaded_png}")
            shutil.copy(downloaded_png, os.path.join(assets_dir, png_name))
        elif os.path.exists(SOURCE_PNG_PLACEHOLDER):
             print(f"  Warning: Downloaded PNG not found, using placeholder.")
             shutil.copy(SOURCE_PNG_PLACEHOLDER, os.path.join(assets_dir, png_name))
        else:
             print(f"  Warning: Source PNG not found at {SOURCE_PNG_PLACEHOLDER}")
             # Create dummy
             with open(os.path.join(assets_dir, png_name), 'w') as f:
                f.write("dummy png")

        # 3. Military Symbol
        generate_mil_symbol(en_name, symbol_desc, assets_dir)

        # Update JSON paths
        # modelUrlSlim -> thumbnail
        # modelUrlFat -> glb
        # modelUrlSymbols -> mil symbol
        
        # Note: The template has complex structure.
        # modelUrlSymbols is a list.
        current_agent['modelUrlSymbols'] = [
            {
                "symbolSeries": 1,
                "symbolName": f"{en_name}/{png_name}", 
                "thumbnail": f"{en_name}/{png_name}"
            },
            {
                "symbolSeries": 2,
                "symbolName": f"{en_name}/{mil_name}", 
                "thumbnail": f"{en_name}/{mil_name}"
            }
        ]
        current_agent['modelUrlSlim'] = f"{en_name}/{glb_name}"
        current_agent['modelUrlFat'] = f"{en_name}/{glb_name}"
        
        # Dynamics
        # Excel says "vehicleSimple". Template uses "iagnt_dynamics_vehicle_simple".
        # We can keep the template's dynamics as it is likely correct for vehicles.
        # Just ensure the list is correct.
        # The template has:
        # "missionableDynamics": [{"dynPluginName": "iagnt_dynamics_vehicle_simple", ...}]
        # So we don't need to change it if it's already vehicle simple.
        
        # Save JSON
        json_path = os.path.join(model_dir, "agent.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(agent_data, f, ensure_ascii=False, indent=4)
            
        print(f"Created package for {en_name}")

if __name__ == "__main__":
    main()
