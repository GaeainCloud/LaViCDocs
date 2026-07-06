import json
from pathlib import Path

from config import MODELS_DIR
from logger import get_logger
from utils.mil_symbol import generate_military_symbol

log = get_logger(__name__)

ASSETS_DIR = MODELS_DIR / "assets"

# Drone Configuration
DRONE_CONFIGS = {
    "大疆Matrice 300RTK无人机.json": {
        "name": "大疆Matrice 300RTK无人机",
        "symbol_desc": "Friendly Rotary Wing Unmanned Aerial Vehicle"
    },
    "亿航EH216-S无人机.json": {
        "name": "亿航EH216-S无人机",
        "symbol_desc": "Friendly Rotary Wing Unmanned Aerial Vehicle"
    },
    "峰飞CarrayAll无人机.json": {
        "name": "峰飞CarrayAll无人机",
        "symbol_desc": "Friendly Fixed Wing Unmanned Aerial Vehicle"
    },
    "沃飞长空AE200.json": {
        "name": "沃飞长空AE200",
        "symbol_desc": "Friendly Fixed Wing Unmanned Aerial Vehicle"
    },
    "纵横CW-15.json": {
        "name": "纵横CW-15",
        "symbol_desc": "Friendly Fixed Wing Unmanned Aerial Vehicle"
    }
}

def update_json(json_filename, png_filename):
    agent_path = MODELS_DIR / json_filename
    if not agent_path.exists():
        log.error(f"{json_filename} not found!")
        return

    with open(agent_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            log.error(f"Invalid JSON in {json_filename}")
            return

    is_list = isinstance(data, list)
    agent = data[0] if is_list and len(data) > 0 else data if not is_list else None
    if agent is None:
        log.error("Empty list in JSON")
        return

    rel_png = f"assets/{png_filename}"

    if "modelUrlSymbols" not in agent:
        agent["modelUrlSymbols"] = []

    found = False
    for sym in agent["modelUrlSymbols"]:
        if sym.get("symbolSeries") == 2:
            sym["symbolName"] = rel_png
            sym["thumbnail"] = rel_png
            found = True
            break

    if not found:
        agent["modelUrlSymbols"].append({
            "symbolSeries": 2,
            "symbolName": rel_png,
            "thumbnail": rel_png
        })

    to_write = [agent] if is_list else agent
    with open(agent_path, 'w', encoding='utf-8') as f:
        json.dump(to_write, f, indent=2, ensure_ascii=False)
    log.info(f"Updated {json_filename} with military symbol")

def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    for json_filename, config in DRONE_CONFIGS.items():
        png_filename = generate_military_symbol(
            config['name'], config['symbol_desc'], ASSETS_DIR
        )
        if png_filename:
            update_json(json_filename, png_filename)

if __name__ == "__main__":
    main()
