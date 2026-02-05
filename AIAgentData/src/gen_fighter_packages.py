import pandas as pd
import json
import os
import requests
import shutil
import zipfile
import re
import math
import time
from bs4 import BeautifulSoup
import military_symbol
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from download_helper import fetch_image_via_helper
import trimesh
import numpy as np

# --- Configuration ---
BASE_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData"
MODELS_DIR = os.path.join(BASE_DIR, "models")
DOWNLOADS_DIR = os.path.join(MODELS_DIR, "downloads")
EXCEL_PATH = os.path.join(MODELS_DIR, "12_15新战斗机仿真模型信息.xlsx")
TEMPLATE_JSON_PATH = os.path.join(BASE_DIR, "examples", "02aircraftAgent.json")

RODIN_API_KEY = "k9TcfFoEhNd9cCPP2guHAHHHkctZHIRhZDywZ1euGUXwihbYLpOjQhofby80NJez"
PROXY_URL = "http://127.0.0.1:7897"

# Set Proxy
os.environ["HTTP_PROXY"] = PROXY_URL
os.environ["HTTPS_PROXY"] = PROXY_URL

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

NAME_MAP = {
    "F-22猛禽战斗机": "F-22_Raptor",
    "F-35闪电II战斗机": "F-35_Lightning_II",
    "Su-57威罪战斗机": "Su-57_Felon",
    "J-20威龙战斗机": "J-20_Mighty_Dragon"
}

SEARCH_TERMS = {
    "F-22猛禽战斗机": "F-22 Raptor fighter jet 3d studio render white background",
    "F-35闪电II战斗机": "F-35 Lightning II fighter jet 3d studio render white background",
    "Su-57威罪战斗机": "Su-57 Felon fighter jet 3d studio render white background",
    "J-20威龙战斗机": "Chengdu J-20 Mighty Dragon fighter jet 3d studio render white background"
}

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def parse_dynamics(text):
    """
    Parse string like:
    最大速度：670 m/s
    最小速度：70 m/s
    最大加速度：25 m/s²
    着舰距离：1500 m
    最大角速度：35 deg/s
    """
    params = {}
    
    # Regex patterns
    v_max_match = re.search(r"最大速度[：:]\s*(\d+(\.\d+)?)", text)
    v_min_match = re.search(r"最小速度[：:]\s*(\d+(\.\d+)?)", text)
    a_max_match = re.search(r"最大加速度[：:]\s*(\d+(\.\d+)?)", text)
    landing_dist_match = re.search(r"着舰距离[：:]\s*(\d+(\.\d+)?)", text)
    omega_max_match = re.search(r"最大角速度[：:]\s*(\d+(\.\d+)?)", text)
    
    if v_max_match: params["V_max"] = float(v_max_match.group(1))
    if v_min_match: params["V_min"] = float(v_min_match.group(1))
    if a_max_match: params["a_max"] = float(a_max_match.group(1))
    if landing_dist_match: params["landing_distance"] = float(landing_dist_match.group(1))
    if omega_max_match: 
        deg = float(omega_max_match.group(1))
        params["omega_max"] = round(deg * math.pi / 180.0, 2) # Convert to rad/s
        
    return params

def fetch_image(model_name, search_term):
    print(f"[{model_name}] Fetching images for '{search_term}'...")
    ensure_dir(DOWNLOADS_DIR)
    target_path = os.path.join(DOWNLOADS_DIR, f"{model_name}.png")
    
    if os.path.exists(target_path):
        print(f"[{model_name}] Image already exists.")
        return target_path

    # Simple Google Search scraping (simulated via known sources or direct duckduckgo/bing api if available, but here scraping generic URLs or using placeholders)
    # Since I cannot easily scrape Google Images without a complex setup, I will use Wikipedia or specific military sites if possible.
    # Alternatively, I can try to use the Rodin generated thumbnail if I can't find one? 
    # But better to try to find one.
    
    # I'll use a search query on a site like Bing or similar if accessible, or just try to find via a direct search engine result page parsing.
    # Given the environment, I'll try a few known sources or just search.
    
    search_url = f"https://www.bing.com/images/search?q={search_term}&qft=+filterui:imagesize-large"
    
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            # Bing images are tricky to scrape directly due to JS.
            # Let's try a simpler approach: Wikipedia API or similar?
            # Or just assume I can find one on a military site.
            pass
    except:
        pass

    # Fallback: Use a generic placeholder if download fails, or try specifically some known URLs.
    # For now, I'll try to use a specific high-probability URL pattern or just skip and let the user know.
    # ACTUALLY, I will try to use `requests` to get a few candidates from a search engine result page HTML (duckduckgo html is easier).
    
    ddg_url = f"https://duckduckgo.com/html/?q={search_term}"
    try:
        resp = requests.get(ddg_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            images = soup.find_all('img', class_='tile--img__img')
            if images:
                img_url = "https:" + images[0]['src'] if images[0]['src'].startswith('//') else images[0]['src']
                # DuckDuckGo images are often thumbnails.
                # Let's try to get the real URL from the `a` tag `href`.
                # Actually, simply getting the thumbnail is often "good enough" for a start if resolution > 400.
                
                print(f"[{model_name}] Downloading image from {img_url}...")
                r = requests.get(img_url, headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    with open(target_path, 'wb') as f:
                        f.write(r.content)
                    return target_path
    except Exception as e:
        print(f"[{model_name}] Image search failed: {e}")

    return None

def generate_symbol(model_name):
    print(f"[{model_name}] Generating military symbol...")
    target_path = os.path.join(DOWNLOADS_DIR, f"{model_name}_mil.png")
    if os.path.exists(target_path):
        return target_path
        
    try:
        # SIDC for Friend, Air, Fixed Wing, Fighter (2525D)
        sidc = "10030102011203000000"
        
        svg_string = None
        if hasattr(military_symbol, 'get_symbol_svg_string_from_sidc'):
            svg_string = military_symbol.get_symbol_svg_string_from_sidc(sidc, style='light', bounding_padding=4)
        elif hasattr(military_symbol, 'get_symbol_svg_string'):
             svg_string = military_symbol.get_symbol_svg_string(sidc, style='light', bounding_padding=4)
        else:
             # Fallback to name with explicit affiliation
             svg_string = military_symbol.get_symbol_svg_string_from_name("Friend Fixed Wing Fighter", style='light', bounding_padding=4, use_variants=True)
        
        if not svg_string:
            raise Exception("Could not generate SVG string")

        temp_svg = os.path.join(DOWNLOADS_DIR, f"{model_name}_mil.svg")
        with open(temp_svg, 'w', encoding='utf-8') as f:
            f.write(svg_string)
            
        drawing = svg2rlg(temp_svg)
        renderPM.drawToFile(drawing, target_path, fmt="PNG")
        return target_path
    except Exception as e:
        print(f"[{model_name}] Symbol generation failed: {e}")
        return None

def process_glb_rotation(file_path):
    """
    Standardize GLB orientation:
    1. Rotate -90 around X (Z-up to Y-up)
    2. Rotate 180 around Y (Correct Facing)
    """
    print(f"Standardizing GLB orientation for {os.path.basename(file_path)}...")
    try:
        # Load
        scene = trimesh.load(file_path, force='scene')
        
        # 1. Rotate -90 around X (Z-up to Y-up)
        # Matrix: [[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]]
        rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
        scene.apply_transform(rot_x)
        
        # 2. Rotate 180 around Y (Facing)
        # Assuming model needs to be rotated 180 degrees around vertical axis (Y in Y-up system)
        rot_y = trimesh.transformations.rotation_matrix(np.radians(180), [0, 1, 0])
        scene.apply_transform(rot_y)
        
        # Export
        data = trimesh.exchange.gltf.export_glb(scene)
        with open(file_path, 'wb') as f:
            f.write(data)
        print("  Orientation fixed.")
    except Exception as e:
        print(f"  Error fixing orientation: {e}")

def generate_glb_rodin(model_name, search_term, image_path):
    print(f"[{model_name}] Generating 3D model with Rodin...")
    ensure_dir(DOWNLOADS_DIR)
    target_path = os.path.join(DOWNLOADS_DIR, f"{model_name}_AI_Rodin.glb")
    
    if os.path.exists(target_path):
        print(f"[{model_name}] GLB already exists.")
        return target_path

    if not image_path or not os.path.exists(image_path):
        print(f"[{model_name}] No image found. Switching to Text-to-3D mode.")
        image_path = None

    headers = {
        "Authorization": f"Bearer {RODIN_API_KEY}",
        "User-Agent": "blender-mcp"
    }
    
    try:
        files = []
        if image_path:
            files.append(("images", ("0000.png", open(image_path, "rb"))))
            
        files.append(("tier", (None, "Sketch")))
        files.append(("mesh_mode", (None, "Raw")))
        files.append(("prompt", (None, f"{search_term}, high quality, realistic 3d asset")))
        
        # Use the correct API endpoint
        url = "https://api.hyper3d.com/api/v2/rodin"
        
        print(f"[{model_name}] Sending request to {url} (Mode: {'Image-to-3D' if image_path else 'Text-to-3D'})...")
        resp = requests.post(url, headers=headers, files=files)
        if resp.status_code not in [200, 201]:
            print(f"[{model_name}] Rodin Create Failed: {resp.text}")
            return None
            
        data = resp.json()
        uuid = data.get("uuid")
        sub_key = data.get("jobs", {}).get("subscription_key") or data.get("subscription_key")
        
        print(f"[{model_name}] Job started. UUID: {uuid}")
        
        # Poll
        for _ in range(120): # 10 minutes max
            time.sleep(5)
            r_status = requests.post("https://api.hyper3d.com/api/v2/status", headers=headers, json={"subscription_key": sub_key})
            if r_status.status_code not in [200, 201]:
                print(f"[{model_name}] Status check failed: {r_status.status_code} - {r_status.text}")
                continue
            
            status_data = r_status.json()
            # print(f"[{model_name}] Status data: {status_data}") # Debug
            statuses = [j["status"] for j in status_data.get("jobs", [])]
            
            if not statuses:
                print(f"[{model_name}] No jobs found in status response.")
                continue

            if all(s == "Done" for s in statuses):
                print(f"[{model_name}] Generation Done!")
                break
            if any(s == "Failed" for s in statuses):
                print(f"[{model_name}] Rodin Job Failed: {statuses}")
                return None
        else:
            print(f"[{model_name}] Timeout waiting for Rodin.")
            return None
            
        # Download
        r_down = requests.post("https://api.hyper3d.com/api/v2/download", headers=headers, json={'task_uuid': uuid})
        d_data = r_down.json()
        glb_url = next((i["url"] for i in d_data.get("list", []) if i["name"].endswith(".glb")), None)
        
        if glb_url:
            r_glb = requests.get(glb_url, stream=True)
            with open(target_path, 'wb') as f:
                shutil.copyfileobj(r_glb.raw, f)
            
            # Post-process rotation
            process_glb_rotation(target_path)
            
            return target_path
            
    except Exception as e:
        print(f"[{model_name}] Rodin Error: {e}")
        
    return None

def create_package(model_name, cn_name, desc, dynamics_params, assets):
    print(f"[{model_name}] Creating package...")
    
    # Structure
    pkg_dir = os.path.join(MODELS_DIR, model_name)
    inner_dir = os.path.join(pkg_dir, model_name)
    ensure_dir(inner_dir)
    
    # Copy Assets
    if assets["img"]: shutil.copy2(assets["img"], os.path.join(inner_dir, f"{model_name}.png"))
    if assets["mil"]: shutil.copy2(assets["mil"], os.path.join(inner_dir, f"{model_name}_mil.png"))
    if assets["glb"]: shutil.copy2(assets["glb"], os.path.join(inner_dir, f"{model_name}_AI_Rodin.glb"))
    
    # Load Template
    with open(TEMPLATE_JSON_PATH, 'r', encoding='utf-8') as f:
        template = json.load(f)
        
    # Modify
    agent = template[0] if isinstance(template, list) else template
    agent["agentName"] = cn_name
    agent["agentNameI18n"] = cn_name
    agent["agentDesc"] = desc
    agent["modelUrlSlim"] = f"{model_name}/{model_name}_AI_Rodin.glb"
    agent["modelUrlFat"] = f"{model_name}/{model_name}_AI_Rodin.glb"
    agent["thumbnail"] = f"{model_name}/{model_name}.png"
    agent["modelUrlSymbols"] = [{
        "symbolSeries": 1,
        "symbolName": f"{model_name}/{model_name}_mil.png",
        "thumbnail": f"{model_name}/{model_name}.png"
    }]

    # Update nested "model" object
    if "model" in agent and isinstance(agent["model"], dict):
        m = agent["model"]
        m["modelName"] = cn_name
        m["introduction"] = desc
        
        # thumbnail
        if "thumbnail" in m and isinstance(m["thumbnail"], dict):
            m["thumbnail"]["url"] = f"{model_name}/{model_name}.png"
            m["thumbnail"]["ossSig"] = f"{model_name}.png"
            
        # mapIconUrl
        if "mapIconUrl" in m and isinstance(m["mapIconUrl"], dict):
            m["mapIconUrl"]["url"] = f"{model_name}/{model_name}_mil.png"
            m["mapIconUrl"]["ossSig"] = f"{model_name}_mil.png"
            
        # dimModelUrls
        if "dimModelUrls" in m and isinstance(m["dimModelUrls"], list) and len(m["dimModelUrls"]) > 0:
            m["dimModelUrls"][0]["url"] = f"{model_name}/{model_name}_AI_Rodin.glb"
            m["dimModelUrls"][0]["ossSig"] = f"{model_name}_AI_Rodin.glb"
    
    # Update Dynamics
    # "dynSettings": "{\"freqdistPlugin\":null...}" - It's a stringified JSON!
    dyn_config = agent["missionableDynamics"][0]
    dyn_settings_str = dyn_config["dynSettings"]["pluginDefaultSettings"]
    dyn_settings = json.loads(dyn_settings_str)
    
    # Apply params
    ds = dyn_settings["dynSettings"]
    if "V_max" in dynamics_params: ds["V_max"] = dynamics_params["V_max"]
    if "V_min" in dynamics_params: ds["V_min"] = dynamics_params["V_min"]
    if "a_max" in dynamics_params: ds["a_max"] = dynamics_params["a_max"]
    if "landing_distance" in dynamics_params: ds["landing_distance"] = dynamics_params["landing_distance"]
    if "omega_max" in dynamics_params: ds["omega_max"] = dynamics_params["omega_max"]
    
    # Save back
    dyn_config["dynSettings"]["pluginDefaultSettings"] = json.dumps(dyn_settings, ensure_ascii=False)
    
    # Write agent.json
    with open(os.path.join(pkg_dir, "agent.json"), 'w', encoding='utf-8') as f:
        # Wrap in list as per LaViC standard
        json.dump([agent], f, indent=4, ensure_ascii=False)
        
    # Zip
    zip_path = os.path.join(MODELS_DIR, f"{model_name}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(pkg_dir, "agent.json"), "agent.json")
        for f in os.listdir(inner_dir):
            zf.write(os.path.join(inner_dir, f), f"{model_name}/{f}")
            
    print(f"[{model_name}] Package created at {zip_path}")

def main():
    df = pd.read_excel(EXCEL_PATH)
    
    for index, row in df.iterrows():
        cn_name = row['文本']  # Changed from '仿真模型名称'
        if cn_name not in NAME_MAP:
            print(f"Skipping unknown model: {cn_name}")
            continue
            
        model_name = NAME_MAP[cn_name]
        search_term = SEARCH_TERMS[cn_name]
        # Description is long, let's take the first paragraph or summary if possible, or just the whole thing?
        # The column is '使用的动力学和指令说明'. It seems to be very long instructions.
        # Maybe I should use '动力学' column? No, that's the plugin name.
        # The Excel shows "文本" (Name), "基本属性" (Params), "类型" (Type).
        # Let's use '文本' as description if no better one? 
        # Or maybe construct a description from '类型' + '文本'.
        # Actually, the '使用的动力学和指令说明' is the description of the dynamics, not the agent itself.
        # The agent description in json usually is short.
        # Let's use `cn_name` + " - " + row['类型'] as description for now, or just `cn_name`.
        desc = f"{cn_name} ({row['类型']})"
        
        dyn_params = parse_dynamics(row['基本属性']) # Changed from '动力学参数'
        
        print(f"\nProcessing {model_name}...")
        
        # 1. Assets
        img_path = fetch_image(model_name, search_term)
        mil_path = generate_symbol(model_name)
        
        # Use symbol as fallback thumbnail if image fetch failed
        real_img_path = img_path
        if not img_path and mil_path:
            print(f"[{model_name}] Using symbol as thumbnail.")
            img_path = mil_path
            
        glb_path = generate_glb_rodin(model_name, search_term, real_img_path)
        
        assets = {
            "img": img_path,
            "mil": mil_path,
            "glb": glb_path
        }
        
        # 2. Package
        create_package(model_name, cn_name, desc, dyn_params, assets)

if __name__ == "__main__":
    main()
