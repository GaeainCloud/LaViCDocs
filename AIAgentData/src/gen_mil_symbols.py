import os
import json
import military_symbol
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "..", "models")
ASSETS_DIR = os.path.join(MODELS_DIR, "assets")

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

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_symbol(name, desc):
    print(f"Generating symbol for {name} ({desc})...")
    
    # 1. Generate SVG using military_symbol
    try:
        # Use helper function that supports style args
        svg_string = military_symbol.get_symbol_svg_string_from_name(desc, style='light', bounding_padding=4, use_variants=True)
        
        if svg_string is None:
             print(f"  Warning: Could not generate SVG for '{desc}', falling back to 'Friendly Unmanned Aerial Vehicle'")
             svg_string = military_symbol.get_symbol_svg_string_from_name("Friendly Unmanned Aerial Vehicle", style='light', bounding_padding=4, use_variants=True)

        # Save temp SVG
        svg_filename = f"{name}_mil.svg"
        svg_path = os.path.join(ASSETS_DIR, svg_filename)
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_string)
            
        # 2. Convert to PNG using svglib
        png_filename = f"{name}_mil.png"
        png_path = os.path.join(ASSETS_DIR, png_filename)
        
        drawing = svg2rlg(svg_path)
        renderPM.drawToFile(drawing, png_path, fmt="PNG")
        print(f"  Saved PNG to {png_path}")
        
        return png_filename
        
    except Exception as e:
        print(f"  Error generating symbol for {name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def update_json(json_filename, png_filename):
    agent_path = os.path.join(MODELS_DIR, json_filename)
    if not os.path.exists(agent_path):
        print(f"  Error: {json_filename} not found!")
        return

    with open(agent_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"  Error: Invalid JSON in {json_filename}")
            return

    # Handle list structure
    is_list = isinstance(data, list)
    if is_list:
        if len(data) > 0:
            agent = data[0]
        else:
            print("  Error: Empty list in JSON")
            return
    else:
        agent = data

    rel_png = f"assets/{png_filename}"
    
    # Check if symbol already exists or add it
    if "modelUrlSymbols" not in agent:
        agent["modelUrlSymbols"] = []
    
    # Check if we already have this symbol series (e.g. series 2 for military)
    # Or just append.
    # Let's check if there is a series 2
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

    # Write back
    to_write = [agent] if is_list else agent
    with open(agent_path, 'w', encoding='utf-8') as f:
        json.dump(to_write, f, indent=2, ensure_ascii=False)
    print(f"  Updated {json_filename} with military symbol")

def main():
    ensure_dir(ASSETS_DIR)
    
    for json_filename, config in DRONE_CONFIGS.items():
        png_filename = generate_symbol(config['name'], config['symbol_desc'])
        if png_filename:
            update_json(json_filename, png_filename)

if __name__ == "__main__":
    main()
