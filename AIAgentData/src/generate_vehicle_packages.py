import copy
import pandas as pd
import json
import os
import shutil
import uuid
import time
from pathlib import Path

from config import MODELS_DIR, EXAMPLES_DIR, DOWNLOADS_DIR, DYNAMICS_MAP
from logger import get_logger
from utils.mil_symbol import generate_military_symbol

log = get_logger(__name__)

# Paths (from central config)
EXCEL_PATH = MODELS_DIR / "06_11新车辆仿真模型信息.xlsx"
TEMPLATE_JSON_PATH = EXAMPLES_DIR / "01vehicleAgent.json"

# Source assets to copy (placeholders)
SOURCE_GLB_PLACEHOLDER = MODELS_DIR / "亿航EH216-S无人机" / "亿航EH216-S无人机" / "亿航EH216-S无人机_AI_Rodin.glb"
SOURCE_PNG_PLACEHOLDER = MODELS_DIR / "亿航EH216-S无人机" / "亿航EH216-S无人机" / "亿航EH216-S无人机.png"

# Model Mapping (Index in Excel -> English Name & Symbol Desc)
MODEL_MAPPING = {
    0: {"name": "Dongfeng-15_Missile_Launcher", "symbol_desc": "Friendly Missile Launcher"},
    1: {"name": "M1083_A1P2_Truck", "symbol_desc": "Friendly Cargo Truck"},
    2: {"name": "Polaris_MRZR_Alpha", "symbol_desc": "Friendly Armoured Fighting Vehicle"},
    3: {"name": "Oshkosh_JLTV", "symbol_desc": "Friendly Armoured Fighting Vehicle"},
    4: {"name": "Dongfeng_Mengshi_CSK181", "symbol_desc": "Friendly Armoured Fighting Vehicle"},
    5: {"name": "Norinco_Lynx_CS_VP4", "symbol_desc": "Friendly Armoured Fighting Vehicle"}
}

def main():
    if not EXCEL_PATH.exists():
        log.error(f"Excel file not found: {EXCEL_PATH}")
        return

    # Load Template
    with open(TEMPLATE_JSON_PATH, 'r', encoding='utf-8') as f:
        template_data = json.load(f)

    # Load Excel
    df = pd.read_excel(str(EXCEL_PATH))

    for i, row in df.iterrows():
        if i not in MODEL_MAPPING:
            continue

        model_info = MODEL_MAPPING[i]
        en_name = model_info["name"]
        symbol_desc = model_info["symbol_desc"]
        cn_name = row['文本']
        description = str(row['基本属性']) + "\n类型: " + str(row['类型'])

        log.info(f"Processing {i}: {cn_name} -> {en_name}")

        # Create Directories
        model_dir = MODELS_DIR / en_name
        assets_dir = model_dir / en_name

        if model_dir.exists():
            shutil.rmtree(model_dir)
        assets_dir.mkdir(parents=True)

        # [#18 Fix] Deep copy template to avoid cross-iteration contamination
        agent_data = copy.deepcopy(template_data)
        if isinstance(agent_data, list):
            current_agent = agent_data[0]
        else:
            current_agent = agent_data
            agent_data = [current_agent]

        # Update Fields
        current_agent['agentKey'] = f"AGENTKEY_{uuid.uuid4().int}"
        current_agent['agentName'] = cn_name
        current_agent['agentNameI18n'] = cn_name
        current_agent['agentDesc'] = description

        # [P0-2] 应用动力学映射规则
        dyn_plugin = DYNAMICS_MAP.get("vehicle", "")
        if dyn_plugin:
            dyn_list = current_agent.get("missionableDynamics")
            if isinstance(dyn_list, list) and dyn_list:
                dyn = dyn_list[0]
                if isinstance(dyn, dict):
                    dyn["dynPluginName"] = dyn_plugin
                    dyn["dynKeyword"] = dyn_plugin
                    dyn_settings = dyn.get("dynSettings")
                    if isinstance(dyn_settings, dict):
                        dyn_settings["pluginName"] = dyn_plugin
            log.info(f"  应用动力学插件: {dyn_plugin}")

        # Assets filenames
        glb_name = f"{en_name}_AI_Rodin.glb"
        png_name = f"{en_name}.png"
        mil_name = f"{en_name}_mil.png"

        # Check for downloaded assets
        downloaded_glb = DOWNLOADS_DIR / f"{en_name}.glb"
        downloaded_png = DOWNLOADS_DIR / f"{en_name}.png"

        # Copy/Generate Assets
        # 1. GLB
        if downloaded_glb.exists():
            log.info(f"  Using downloaded GLB: {downloaded_glb}")
            shutil.copy(downloaded_glb, assets_dir / glb_name)
        elif SOURCE_GLB_PLACEHOLDER.exists():
            log.warning(f"  Downloaded GLB not found, using placeholder.")
            shutil.copy(SOURCE_GLB_PLACEHOLDER, assets_dir / glb_name)
        else:
            log.warning(f"  Source GLB not found at {SOURCE_GLB_PLACEHOLDER}")
            (assets_dir / glb_name).write_text("dummy glb")

        # 2. Thumbnail PNG
        if downloaded_png.exists():
            log.info(f"  Using downloaded PNG: {downloaded_png}")
            shutil.copy(downloaded_png, assets_dir / png_name)
        elif SOURCE_PNG_PLACEHOLDER.exists():
            log.warning(f"  Downloaded PNG not found, using placeholder.")
            shutil.copy(SOURCE_PNG_PLACEHOLDER, assets_dir / png_name)
        else:
            log.warning(f"  Source PNG not found at {SOURCE_PNG_PLACEHOLDER}")
            (assets_dir / png_name).write_text("dummy png")

        # 3. Military Symbol (using shared util)
        generate_military_symbol(en_name, symbol_desc, assets_dir)

        # Update JSON paths
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

        # Save JSON
        json_path = model_dir / "agent.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(agent_data, f, ensure_ascii=False, indent=4)

        log.info(f"Created package for {en_name}")

if __name__ == "__main__":
    main()
