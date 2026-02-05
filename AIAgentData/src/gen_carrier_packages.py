import pandas as pd
import json
import os
import requests
import shutil
import zipfile
import re
import math
import time
import random
import military_symbol
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import trimesh
import numpy as np

# --- Configuration ---
# Use raw strings for paths
BASE_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData"
MODELS_DIR = os.path.join(BASE_DIR, "models")
DOWNLOADS_DIR = os.path.join(MODELS_DIR, "downloads")
EXCEL_PATH = os.path.join(MODELS_DIR, "16_21新舰载机仿真模型信息.xlsx")
TEMPLATE_JSON_PATH = os.path.join(BASE_DIR, "examples", "02aircraftAgent.json")

# RODIN API
RODIN_API_KEY = "k9TcfFoEhNd9cCPP2guHAHHHkctZHIRhZDywZ1euGUXwihbYLpOjQhofby80NJez"
PROXY_URL = "http://127.0.0.1:7897"

# Set Proxy
os.environ["HTTP_PROXY"] = PROXY_URL
os.environ["HTTPS_PROXY"] = PROXY_URL

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# English Name Mapping
NAME_MAP = {
    "J-35舰载机": "J-35_Carrier_Variant",
    "F/A-18E/F超级大黄蜂": "FA-18EF_Super_Hornet",
    "Su-33海侧卫舰载机": "Su-33_Flanker-D",
    "阵风M舰载机": "Rafale_M",
    "F-14D超级雄猫舰载机": "F-14D_Super_Tomcat",
    "J-15飞鲨舰载机": "J-15_Flying_Shark",
    "J-10C猛龙": "J-10C_Vigorous_Dragon",
    "J10C战斗机": "J-10C_Vigorous_Dragon",
    "BZK-005侦察机": "BZK-005_Recon_UAV",
    "无侦-7侦察机": "WZ-7_Soaring_Dragon",
    "空警-500": "KJ-500_AEW_C",
    "空警-600": "KJ-600_Carrier_AEW",
    "E-3G预警机": "E-3G_Sentry",
    "E-2D预警机": "E-2D_Advanced_Hawkeye",
    "A-50U预警机": "A-50U_Mainstay",
    "KC-46A加油机": "KC-46A_Pegasus",
    "KC-135加油机": "KC-135_Stratotanker"
}

# Real Image URLs (High Quality / Wiki / RenderHub)
IMAGE_URLS = {
    "J-35_Carrier_Variant": "https://cdn.renderhub.com/mermodels/shenyang-j-35-stealth-fighter/shenyang-j-35-stealth-fighter-01.jpg",
    "FA-18EF_Super_Hornet": "https://upload.wikimedia.org/wikipedia/commons/d/de/US_Navy_071203-N-8923M-074_An_F-A-18F_Super_Hornet%2C_from_the_Red_Rippers_of_Strike_Fighter_Squadron_%28VFA%29_11%2C_makes_a_sharp_turn_above_the_flight_deck_aboard_the_Nimitz-class_nuclear-powered_aircraft_carrier_USS_Harry_S._Truman.jpg",
    "Su-33_Flanker-D": "https://media.sketchfab.com/models/3d3e2c35670f4ebcbe5566e016e2473c/thumbnails/c3558fd4ab6b40299afc85dd4159b4b2/3701c2db4d2a4bb4b1ad512c93b61b42.jpeg",
    "Rafale_M": "https://upload.wikimedia.org/wikipedia/commons/4/42/Rafale_M_of_Flottile_12F_in_flight_2014.JPG",
    "F-14D_Super_Tomcat": "https://media.sketchfab.com/models/ae7f416776f54bdba1642f2f703ef2b0/thumbnails/57f9677241614fef96e2ab90d6478fb7/6724107a1c8d47a798116cee94365779.jpeg",
    "J-15_Flying_Shark": "https://media.sketchfab.com/models/ec6be963f1c14835a2df1ee148ebf576/thumbnails/1d9be6056e37412d8f75d87432938a1a/92a6ea98f2f7480099bfcbf5b05d6003.jpeg",
    "J-10C_Vigorous_Dragon": "https://media.sketchfab.com/models/3a1a1863e9ba44e88d35da0d5f23caeb/thumbnails/702c2907e1a749049f9240be5f32610c/36e9b2d8956a454b8b126a974ad230e4.jpeg",
    "BZK-005_Recon_UAV": "https://upload.wikimedia.org/wikipedia/commons/1/13/Harbin_BZK-005_high_altitude_long_range_UAV.jpg",
    "WZ-7_Soaring_Dragon": "https://upload.wikimedia.org/wikipedia/commons/7/7a/WZ-7_at_Airshow_China_Zhuhai_2022.jpg",
    "KJ-500_AEW_C": "https://upload.wikimedia.org/wikipedia/commons/a/ad/KJ-500_%28cropped%29.jpg",
    "KJ-600_Carrier_AEW": "https://upload.wikimedia.org/wikipedia/commons/9/91/E-2C_Hawkeye.jpg",
    "E-3G_Sentry": "https://upload.wikimedia.org/wikipedia/commons/c/c7/USAF_E-3_Sentry.jpg",
    "E-2D_Advanced_Hawkeye": "https://upload.wikimedia.org/wikipedia/commons/9/91/E-2C_Hawkeye.jpg",
    "A-50U_Mainstay": "https://upload.wikimedia.org/wikipedia/commons/c/c7/USAF_E-3_Sentry.jpg",
    "KC-46A_Pegasus": "https://upload.wikimedia.org/wikipedia/commons/6/64/KC-46A_Pegasus_refuels_a_F-15_Strike_Eagle.jpg",
    "KC-135_Stratotanker": "https://upload.wikimedia.org/wikipedia/commons/2/24/18thopgroup-kc-135.jpg"
}

# SIDC Mapping (FixedWing Fighter)
SIDC_MAP = {
    "default": "30030100001201000000"  # Fighter
}

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def parse_dynamics(text):
    params = {}
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
        params["omega_max"] = round(deg * math.pi / 180.0, 2)
        
    return params

def download_image(url_or_urls, save_path):
    # Always overwrite if requested (re-generation)
    urls = url_or_urls if isinstance(url_or_urls, list) else [url_or_urls]
    
    headers = HEADERS.copy()
    headers["Referer"] = "https://www.google.com/"
    
    for url in urls:
        print(f"Downloading image from {url}...")
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(resp.content)
                    print("  Download success.")
                    return True
                elif resp.status_code == 429:
                    wait_time = random.uniform(20, 40) * (attempt + 1)
                    print(f"  Got 429 Too Many Requests. Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  Failed: {resp.status_code}")
                    # Try next URL if not 429
                    break 
            except Exception as e:
                print(f"  Error downloading (attempt {attempt+1}): {e}")
                time.sleep(2)
                
    return False

def generate_mil_symbol(sidc, save_path):
    print(f"Generating symbol {sidc} to {save_path}...")
    try:
        symbol = military_symbol.get_symbol_svg_string_from_sidc(sidc)
        temp_svg = save_path.replace(".png", "_temp.svg")
        with open(temp_svg, "w", encoding="utf-8") as f:
            f.write(symbol)
        drawing = svg2rlg(temp_svg)
        renderPM.drawToFile(drawing, save_path, fmt="PNG")
        if os.path.exists(temp_svg):
            os.remove(temp_svg)
        return True
    except Exception as e:
        print(f"Error generating symbol: {e}")
        return False

def generate_glb_via_rodin(prompt, image_path, save_path):
    print(f"Generating GLB for '{prompt}' via Rodin...")
    
    # Check if GLB exists and is valid (not empty)
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
        # Force overwrite as user requested "re-generate"
        # print(f"  [INFO] Overwriting existing GLB...")
        # try:
        #     os.remove(save_path)
        # except:
        #     pass
        print(f"  GLB exists: {save_path}. Skipping generation.")
        return save_path
        # print(f"  [INFO] GLB exists, skipping generation: {save_path}")
        # return save_path
    
    if not image_path or not os.path.exists(image_path):
        print("  [ERROR] No input image for Rodin.")
        return None
        
    headers = {
        "Authorization": f"Bearer {RODIN_API_KEY}",
        "User-Agent": "blender-mcp"
    }
    
    try:
        files = [
            ("images", ("0000.png", open(image_path, "rb"))),
            ("tier", (None, "Sketch")),
            ("mesh_mode", (None, "Raw")),
            ("prompt", (None, f"{prompt}, high quality, realistic 3d asset"))
        ]
        
        print("  Posting job to Rodin...")
        resp = requests.post("https://hyperhuman.deemos.com/api/v2/rodin", headers=headers, files=files)
        if resp.status_code not in [200, 201]:
            print(f"  [ERROR] Rodin Create Failed ({resp.status_code}): {resp.text}")
            return None
            
        data = resp.json()
        uuid = data.get("uuid")
        sub_key = data.get("jobs", {}).get("subscription_key") or data.get("subscription_key")
        
        if not uuid or not sub_key:
            print("  [ERROR] Failed to get UUID or Subscription Key")
            return None
            
        print(f"  Job started. UUID: {uuid}")
        
        # Poll
        for i in range(120): # 10 minutes max
            time.sleep(5)
            try:
                r_status = requests.post("https://hyperhuman.deemos.com/api/v2/status", headers=headers, json={"subscription_key": sub_key}, timeout=10)
                if r_status.status_code not in [200, 201]:
                    print(f"  Polling error ({r_status.status_code}): {r_status.text[:100]}... retrying...")
                    continue
                
                s_data = r_status.json()
                jobs = s_data.get("jobs", [])
                statuses = [j["status"] for j in jobs]
                
                # Only print status every 5th poll to reduce spam, or if it changes
                if i % 6 == 0:
                    print(f"  Poll {i}: Statuses: {statuses}")
                
                if all(s == "Done" for s in statuses):
                    print("  Rodin Job Completed.")
                    break
                if any(s == "Failed" for s in statuses):
                    print(f"  [ERROR] Rodin Job Failed. Statuses: {statuses}")
                    return None
            except Exception as e:
                print(f"  Polling exception: {e}, retrying...")
                continue
        else:
            print("  [ERROR] Timeout waiting for Rodin.")
            return None
            
        # Download with retry
        print("  Downloading result...")
        time.sleep(10) # Wait a bit for backend to be ready
        
        for attempt in range(10):
            try:
                r_down = requests.post("https://hyperhuman.deemos.com/api/v2/download", headers=headers, json={'task_uuid': uuid})
                if r_down.status_code in [200, 201]:
                    break
                print(f"  [WARN] Download init failed ({r_down.status_code}): {r_down.text}. Retrying...")
                time.sleep(5 + attempt * 2)
            except Exception as e:
                 print(f"  [WARN] Download init exception: {e}. Retrying...")
                 time.sleep(5 + attempt * 2)
        else:
            print("  [ERROR] Failed to init download after retries.")
            return None
            
        d_data = r_down.json()
        glb_url = None
        for item in d_data.get("list", []):
            if item["name"].endswith(".glb"):
                glb_url = item["url"]
                break
                
        if glb_url:
            print(f"  Downloading GLB from {glb_url}...")
            r_glb = requests.get(glb_url, stream=True)
            with open(save_path, 'wb') as f:
                shutil.copyfileobj(r_glb.raw, f)
            print(f"  GLB saved to {save_path}")
            return save_path
        else:
            print("  [ERROR] No GLB found in download list.")
            return None
            
    except Exception as e:
        print(f"  [ERROR] Rodin error: {e}")
        return None

def process_glb_rotation_strict(file_path):
    print(f"Standardizing GLB orientation for {os.path.basename(file_path)}...")
    try:
        scene = trimesh.load(file_path, force='scene')
        # 1. Rotate -90 around X (Z-up to Y-up)
        rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
        scene.apply_transform(rot_x)
        # 2. Rotate 180 around Y (Facing)
        rot_y = trimesh.transformations.rotation_matrix(np.radians(180), [0, 1, 0])
        scene.apply_transform(rot_y)
        data = trimesh.exchange.gltf.export_glb(scene)
        with open(file_path, 'wb') as f:
            f.write(data)
        print("  Orientation fixed (Strict X-90, Y180).")
    except Exception as e:
        print(f"  Error fixing orientation: {e}")

def create_package(row):
    cn_name = row['文本'].strip()
    desc = row.get('感知能力', '') + "\n" + row.get('通信能力', '')
    dynamics_str = row['动力学']
    attrs = parse_dynamics(row['基本属性'])
    
    if cn_name not in NAME_MAP:
        print(f"Skipping unknown model: {cn_name}")
        return
        
    en_name = NAME_MAP[cn_name]
    print(f"Processing {cn_name} -> {en_name}...")
    
    model_dir = os.path.join(MODELS_DIR, en_name)
    assets_dir = os.path.join(model_dir, en_name)
    ensure_dir(assets_dir)
    ensure_dir(DOWNLOADS_DIR)
    
    # 1. Agent.json
    with open(TEMPLATE_JSON_PATH, 'r', encoding='utf-8') as f:
        agent = json.load(f)[0]
        
    def smart_num(val):
        if isinstance(val, (int, float)):
            return int(val) if val == int(val) else val
        return val

    agent['agentName'] = cn_name
    agent['agentNameI18n'] = cn_name
    # agent['agentType'] = "FixedWing" # User requested Instagent from template
    agent['dynamics'] = dynamics_str
    agent['agentIntroduction'] = desc
    agent['agentDesc'] = desc
    
    if 'dynamicsParams' not in agent:
        agent['dynamicsParams'] = {}
    agent['dynamicsParams']['V_max'] = smart_num(attrs.get('V_max', 340))
    agent['dynamicsParams']['V_min'] = smart_num(attrs.get('V_min', 60))
    agent['dynamicsParams']['a_max'] = smart_num(attrs.get('a_max', 15))
    agent['dynamicsParams']['landing_distance'] = smart_num(attrs.get('landing_distance', 1000))
    agent['dynamicsParams']['omega_max'] = smart_num(attrs.get('omega_max', 0.5))

    if "missionableDynamics" in agent and len(agent["missionableDynamics"]) > 0:
        dyn_config = agent["missionableDynamics"][0]
        if "dynSettings" in dyn_config and "pluginDefaultSettings" in dyn_config["dynSettings"]:
            try:
                dyn_settings_str = dyn_config["dynSettings"]["pluginDefaultSettings"]
                dyn_settings = json.loads(dyn_settings_str)
                if "dynSettings" in dyn_settings:
                    ds = dyn_settings["dynSettings"]
                    ds["V_max"] = smart_num(attrs.get('V_max', ds.get("V_max", 340)))
                    ds["V_min"] = smart_num(attrs.get('V_min', ds.get("V_min", 60)))
                    ds["a_max"] = smart_num(attrs.get('a_max', ds.get("a_max", 15)))
                    ds["landing_distance"] = smart_num(attrs.get('landing_distance', ds.get("landing_distance", 1000)))
                    ds["omega_max"] = smart_num(attrs.get('omega_max', ds.get("omega_max", 0.5)))
                dyn_config["dynSettings"]["pluginDefaultSettings"] = json.dumps(dyn_settings, ensure_ascii=False)
            except Exception as e:
                print(f"  [WARN] Failed to update nested dynamics: {e}")
    
    agent['modelUrlSlim'] = f"{en_name}/{en_name}_AI_Rodin.glb"
    agent['modelUrlFat'] = f"{en_name}/{en_name}_AI_Rodin.glb"
    
    if 'modelUrlSymbols' in agent and isinstance(agent['modelUrlSymbols'], list) and len(agent['modelUrlSymbols']) > 0:
        agent['modelUrlSymbols'][0]['symbolName'] = f"{en_name}/{en_name}_mil.png"
        agent['modelUrlSymbols'][0]['thumbnail'] = f"{en_name}/{en_name}.png"
    else:
        agent['modelUrlSymbols'] = [{
            "symbolSeries": 1,
            "symbolName": f"{en_name}/{en_name}_mil.png",
            "thumbnail": f"{en_name}/{en_name}.png"
        }]
    
    # Ensure 'model' field exists
    if "model" not in agent:
        agent["model"] = {}
        
    if isinstance(agent["model"], dict):
        m = agent["model"]
        m["modelName"] = cn_name
        m["introduction"] = desc
        
        # Ensure thumbnail object exists
        if "thumbnail" not in m or not isinstance(m["thumbnail"], dict):
            m["thumbnail"] = {}
        m["thumbnail"]["url"] = f"{en_name}/{en_name}.png"
        m["thumbnail"]["ossSig"] = f"{en_name}.png"
        
        # Ensure mapIconUrl object exists
        if "mapIconUrl" not in m or not isinstance(m["mapIconUrl"], dict):
            m["mapIconUrl"] = {}
        m["mapIconUrl"]["url"] = f"{en_name}/{en_name}_mil.png"
        m["mapIconUrl"]["ossSig"] = f"{en_name}_mil.png"
        
        # Ensure dimModelUrls list exists
        if "dimModelUrls" not in m or not isinstance(m["dimModelUrls"], list):
            m["dimModelUrls"] = [{}]
        if len(m["dimModelUrls"]) == 0:
            m["dimModelUrls"].append({})
            
        m["dimModelUrls"][0]["url"] = f"{en_name}/{en_name}_AI_Rodin.glb"
        m["dimModelUrls"][0]["ossSig"] = f"{en_name}_AI_Rodin.glb"

    with open(os.path.join(model_dir, "agent.json"), 'w', encoding='utf-8') as f:
        json.dump([agent], f, indent=4, ensure_ascii=False)
        
    # 2. Assets
    # Image
    img_url = IMAGE_URLS.get(en_name)
    img_download_path = os.path.join(DOWNLOADS_DIR, f"{en_name}.png")
    img_dst = os.path.join(assets_dir, f"{en_name}.png")
    
    if img_url:
        if download_image(img_url, img_download_path):
            shutil.copy(img_download_path, img_dst)
        else:
            print(f"  [MISSING] Failed to download image for {en_name}")
    else:
        print(f"  [MISSING] No image URL for {en_name}")
        
    # Symbol
    sym_dst = os.path.join(assets_dir, f"{en_name}_mil.png")
    generate_mil_symbol(SIDC_MAP['default'], sym_dst)
    
    # GLB
    glb_download_path = os.path.join(DOWNLOADS_DIR, f"{en_name}_AI_Rodin.glb")
    glb_dst = os.path.join(assets_dir, f"{en_name}_AI_Rodin.glb")
    
    # Try to generate/download GLB
    prompt = f"{cn_name}, {en_name}, high quality military aircraft"
    
    saved_glb = generate_glb_via_rodin(prompt, img_download_path, glb_download_path)
    
    if saved_glb and os.path.exists(saved_glb):
        shutil.copy(saved_glb, glb_dst)
        process_glb_rotation_strict(glb_dst)
    else:
        print(f"  [MISSING] Failed to generate GLB for {en_name}")
        
    # 3. Zip
    zip_path = os.path.join(MODELS_DIR, f"{en_name}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(os.path.join(model_dir, "agent.json"), arcname="agent.json")
        for root, _, files in os.walk(assets_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, model_dir)
                zipf.write(file_path, arcname=rel_path)
                
    print(f"  Package created: {zip_path}")

def main():
    try:
        df = pd.read_excel(EXCEL_PATH)
        
        # Inject J-10C data if not present
        if "J-10C猛龙" not in df['文本'].values:
            print("Injecting J-10C data...")
            new_row = {
                '文本': "J-10C猛龙",
                '感知能力': "装备有源相控阵雷达(AESA)，具备强大的对空、对地、对海探测能力。",
                '通信能力': "具备数据链通信能力，可与预警机、其他战机进行协同作战。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft", # Use template dynamics
                '基本属性': "最大速度：2.2马赫 最小速度：200km/h 最大加速度：9g 着舰距离：800m 最大角速度：30度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
        # Inject J10C战斗机 data if not present (Copy of J-10C猛龙)
        if "J10C战斗机" not in df['文本'].values:
            print("Injecting J10C战斗机 data...")
            new_row = {
                '文本': "J10C战斗机",
                '感知能力': "装备有源相控阵雷达(AESA)，具备强大的对空、对地、对海探测能力。",
                '通信能力': "具备数据链通信能力，可与预警机、其他战机进行协同作战。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft", # Use template dynamics
                '基本属性': "最大速度：2.2马赫 最小速度：200km/h 最大加速度：9g 着舰距离：800m 最大角速度：30度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject Su-33 data if not present
        if "Su-33海侧卫舰载机" not in df['文本'].values:
            print("Injecting Su-33 data...")
            new_row = {
                '文本': "Su-33海侧卫舰载机",
                '感知能力': "装备强大的机载雷达和光电探测系统，具备超视距空战和对海攻击能力。",
                '通信能力': "配备先进的数据链和通信设备，支持与航母及其他飞机的协同作战。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：2.17马赫 最小速度：240km/h 最大加速度：8g 着舰距离：100m 最大角速度：25度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject F-14D data if not present
        if "F-14D超级雄猫舰载机" not in df['文本'].values:
            print("Injecting F-14D data...")
            new_row = {
                '文本': "F-14D超级雄猫舰载机",
                '感知能力': "装备AN/APG-71雷达和红外搜索跟踪系统(IRST)，具备强大的多目标跟踪和远程截击能力。",
                '通信能力': "配备JTIDS数据链，支持与E-2C预警机和航母战斗群的高速数据共享。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：2.34马赫 最小速度：240km/h 最大加速度：7.5g 着舰距离：150m 最大角速度：22度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject J-15 data if not present
        if "J-15飞鲨舰载机" not in df['文本'].values:
            print("Injecting J-15 data...")
            new_row = {
                '文本': "J-15飞鲨舰载机",
                '感知能力': "装备多普勒脉冲雷达或有源相控阵雷达，具备完善的对空、对海搜索与火控能力。",
                '通信能力': "配备综合数据链系统，支持与航母编队及预警机的高速信息交互。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：2.4马赫 最小速度：240km/h 最大加速度：8.5g 着舰距离：120m 最大角速度：24度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject BZK-005 data if not present
        if "BZK-005侦察机" not in df['文本'].values:
            print("Injecting BZK-005 data...")
            new_row = {
                '文本': "BZK-005侦察机",
                '感知能力': "中高空远程无人侦察机(MALE UAV)，具备全天候侦察能力，配备光电吊舱和卫星通信链路。",
                '通信能力': "配备宽带卫星数据链，支持远程实时图像传输和超视距控制，续航时间长达40小时。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：210km/h 最小速度：100km/h 最大加速度：3g 着舰距离：650m 最大角速度：20度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject WZ-7 data if not present
        if "无侦-7侦察机" not in df['文本'].values:
            print("Injecting WZ-7 data...")
            new_row = {
                '文本': "无侦-7侦察机",
                '感知能力': "配备高性能合成孔径雷达和光电侦察设备，具备高空长航时全天候侦察监视能力。",
                '通信能力': "具备高带宽卫星通信和视距数据链，可实时传输高分辨率图像和情报数据。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：750km/h 最小速度：150km/h 最大加速度：4g 着舰距离：800m 最大角速度：15度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject KJ-500 data if not present
        if "空警-500" not in df['文本'].values:
            print("Injecting KJ-500 data...")
            new_row = {
                '文本': "空警-500",
                '感知能力': "配备数字阵列有源相控阵雷达，实现360度全方位覆盖，具备强大的空中预警、指挥引导和电子侦察能力。",
                '通信能力': "具备高速宽带数据链和卫星通信能力，可作为空中指挥枢纽，实现多平台信息融合与分发。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：550km/h 最小速度：180km/h 最大加速度：3g 着舰距离：1000m 最大角速度：10度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject KJ-600 data if not present
        if "空警-600" not in df['文本'].values:
            print("Injecting KJ-600 data...")
            new_row = {
                '文本': "空警-600",
                '感知能力': "配备先进有源相控阵雷达，具备对海对空远程探测能力，可引导舰载机进行超视距攻击。",
                '通信能力': "具备强大的指挥控制和数据链中继能力，是航母编队的空中指挥中心。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：693km/h 最小速度：180km/h 最大加速度：4g 着舰距离：800m 最大角速度：12度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject E-3G data if not present
        if "E-3G预警机" not in df['文本'].values:
            print("Injecting E-3G data...")
            new_row = {
                '文本': "E-3G预警机",
                '感知能力': "配备AN/APY-2无源相控阵雷达（Block 40/45升级），具备全天候远程空中预警、敌我识别和战场管理能力。",
                '通信能力': "集成Link 16、卫星通信及高频/超高频无线电，作为空中指挥控制中心（AWACS）协调联合作战。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：855km/h 最小速度：260km/h 最大加速度：2.5g 着舰距离：1500m 最大角速度：10度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject E-2D data if not present
        if "E-2D预警机" not in df['文本'].values:
            print("Injecting E-2D data...")
            new_row = {
                '文本': "E-2D预警机",
                '感知能力': "配备AN/APY-9有源相控阵雷达，具备“数字四分卫”能力，支持海军综合火控防空（NIFC-CA）和导弹制导。",
                '通信能力': "集成Link 16、TTNT（战术瞄准网络技术）及卫星通信，实现航母打击群与远征打击群的无缝连接。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：648km/h 最小速度：180km/h 最大加速度：3g 着舰距离：800m 最大角速度：12度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject A-50U data if not present
        if "A-50U预警机" not in df['文本'].values:
            print("Injecting A-50U data...")
            new_row = {
                '文本': "A-50U预警机",
                '感知能力': "配备Shmel-M有源相控阵雷达，可探测800公里外的空中目标，具备同时跟踪300个目标并引导战斗机拦截的能力。",
                '通信能力': "集成先进的数据链和卫星通信系统，作为空中指挥所协调陆海空联合作战。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：900km/h 最小速度：240km/h 最大加速度：2g 着舰距离：2000m 最大角速度：8度/秒"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject KC-46A data if not present
        if "KC-46A加油机" not in df['文本'].values:
            print("Injecting KC-46A data...")
            new_row = {
                '文本': "KC-46A加油机",
                '感知能力': "配备ALR-69A雷达告警接收机和红外对抗系统，具备全向威胁感知能力；拥有先进的驾驶舱数字显示系统，可实时监控燃油状态和战场态势。",
                '通信能力': "集成Link 16数据链、卫星通信和抗干扰语音通信系统，作为空中通信节点支持网络中心战。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：915km/h 巡航速度：851km/h 航程：11830km 加油能力：96000kg燃油载荷 最大起飞重量：188000kg"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Inject KC-135 data if not present
        if "KC-135加油机" not in df['文本'].values:
            print("Injecting KC-135 data...")
            new_row = {
                '文本': "KC-135加油机",
                '感知能力': "配备气象雷达和改进的导航/通信系统，具备全天候飞行能力；拥有现代化的驾驶舱航空电子系统。",
                '通信能力': "集成UHF/VHF/HF无线电和卫星通信系统，支持与受油机和指挥中心的实时通信及数据中继。",
                '动力学': "iagnt_dynamics_carrier_based_aircraft",
                '基本属性': "最大速度：933km/h 巡航速度：853km/h 航程：2419km（满载） 转场航程：17766km 加油能力：90718kg燃油载荷"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        target_models = [
            # "J-35舰载机",
            # "F/A-18E/F超级大黄蜂",
            # "Su-33海侧卫舰载机",
            # "阵风M舰载机",
            # "F-14D超级雄猫舰载机",
            # "J-15飞鲨舰载机",
            # "J-10C猛龙",
            # "J10C战斗机",
            # "BZK-005侦察机",
            # "无侦-7侦察机",
            # "空警-500",
            # "空警-600",
            # "E-3G预警机",
            # "E-2D预警机",
            # "A-50U预警机",
            # "KC-46A加油机",
            "KC-135加油机"
        ]
        
        for _, row in df.iterrows():
            if row['文本'].strip() in target_models:
                create_package(row)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
