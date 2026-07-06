import os
import json
import requests
import time
import shutil
import zipfile
from pathlib import Path

from config import (
    DOWNLOADS_DIR as CFG_DOWNLOADS_DIR,
    MODELS_DIR as CFG_MODELS_DIR,
    apply_proxy_env,
    require_rodin_api_key,
)
from logger import get_logger
from utils.image_utils import fetch_and_select_best, scrape_images_from_page
from utils.glb_utils import rotate_glb_to_yup
from utils.mil_symbol import generate_military_symbol

# --- Configuration ---
MODEL_NAME = "RIM-161_SM-3"
READABLE_NAME = "RIM-161 Standard Missile 3"
SYMBOL_DESC = "Friendly Air Defense Missile" # Or "Friendly Missile"
DOWNLOADS_DIR = str(CFG_DOWNLOADS_DIR)
FINAL_MODELS_DIR = str(CFG_MODELS_DIR)

apply_proxy_env()
log = get_logger(__name__)

# Search URLs for Images
IMAGE_URLS = [
    "https://missilethreat.csis.org/missile/standard-missile-3/",
    "https://en.wikipedia.org/wiki/RIM-161_Standard_Missile_3",
    "https://www.rtx.com/raytheon/what-we-do/sea/sm-3-interceptor",
    "https://upload.wikimedia.org/wikipedia/commons/e/eb/RIM-161_SM-3_missile_launch_from_USS_Lake_Erie_%28CG-70%29_2005.jpg"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# --- 1. Fetch Images ---
def fetch_images():
    log.info(f"Fetching images for {MODEL_NAME}...")
    ensure_dir(DOWNLOADS_DIR)
    candidates = []
    for url in IMAGE_URLS:
        if url.lower().endswith((".jpg", ".png", ".jpeg", ".webp")):
            candidates.append(url)
        else:
            candidates.extend(scrape_images_from_page(url))

    candidates = list(dict.fromkeys(candidates))
    best_image = fetch_and_select_best(candidates, max_candidates=5, query=READABLE_NAME)
    if not best_image:
        log.info("Failed to find any suitable image.")
        return None

    best_image_path = os.path.join(DOWNLOADS_DIR, f"{MODEL_NAME}.png")
    with open(best_image_path, "wb") as f:
        f.write(best_image.data)
    log.info(f"Final image saved to {best_image_path} from {best_image.url}")
    return best_image_path

# --- 2. Generate Military Symbol --- [P0-3] 使用共享模块
def generate_symbol():
    log.info(f"Generating military symbol for {SYMBOL_DESC}...")
    result = generate_military_symbol(
        MODEL_NAME, SYMBOL_DESC, Path(DOWNLOADS_DIR),
        fallback_desc="Friendly Missile"
    )
    if result:
        return os.path.join(DOWNLOADS_DIR, result)
    return None

# --- 3. Generate GLB (Rodin) ---
def generate_glb(image_path):
    log.info("Generating 3D model with Rodin...")
    if not image_path or not os.path.exists(image_path):
        log.info("No input image for Rodin.")
        return None
    try:
        rodin_api_key = require_rodin_api_key()
    except ValueError as e:
        log.info(str(e))
        return None
        
    output_glb = os.path.join(DOWNLOADS_DIR, f"{MODEL_NAME}_AI_Rodin.glb")
    # If already exists, skip (for testing)
    # if os.path.exists(output_glb): return output_glb
    
    headers = {
        "Authorization": f"Bearer {rodin_api_key}",
        "User-Agent": "blender-mcp"
    }
    
    # Create Job
    try:
        files = [
            ("images", ("0000.png", open(image_path, "rb"))),
            ("tier", (None, "Sketch")),
            ("mesh_mode", (None, "Raw")),
            ("prompt", (None, f"{READABLE_NAME}, high quality, realistic 3d missile asset"))
        ]
        
        log.info("Posting job to Rodin...")
        resp = requests.post("https://hyperhuman.deemos.com/api/v2/rodin", headers=headers, files=files)
        if resp.status_code not in [200, 201]:
            log.info(f"Rodin Create Failed: {resp.text}")
            return None
            
        data = resp.json()
        uuid = data.get("uuid")
        sub_key = data.get("jobs", {}).get("subscription_key") or data.get("subscription_key")
        
        if not uuid or not sub_key:
            log.info("Failed to get UUID or Subscription Key")
            return None
            
        log.info(f"Job started. UUID: {uuid}")
        
        # Poll
        while True:
            time.sleep(5)
            r_status = requests.post("https://hyperhuman.deemos.com/api/v2/status", headers=headers, json={"subscription_key": sub_key})
            if r_status.status_code != 200:
                log.info("Polling error")
                continue
                
            s_data = r_status.json()
            jobs = s_data.get("jobs", [])
            statuses = [j["status"] for j in jobs]
            log.info(f"Status: {statuses}")
            
            if all(s == "Done" for s in statuses):
                break
            if any(s == "Failed" for s in statuses):
                log.info("Rodin Job Failed")
                return None
                
        # Download
        log.info("Downloading result...")
        r_down = requests.post("https://hyperhuman.deemos.com/api/v2/download", headers=headers, json={'task_uuid': uuid})
        if r_down.status_code != 200:
            log.info("Download init failed")
            return None
            
        d_data = r_down.json()
        glb_url = None
        for item in d_data.get("list", []):
            if item["name"].endswith(".glb"):
                glb_url = item["url"]
                break
                
        if glb_url:
            log.info(f"Downloading GLB from {glb_url}...")
            r_glb = requests.get(glb_url, stream=True)
            with open(output_glb, 'wb') as f:
                shutil.copyfileobj(r_glb.raw, f)
            rotate_glb_to_yup(Path(output_glb), Path(output_glb))
            log.info(f"GLB saved to {output_glb}")
            return output_glb
            
    except Exception as e:
        log.info(f"Rodin error: {e}")
        return None

# --- 4. Package ---
def package_model():
    log.info("Packaging model...")
    # Create structure
    model_dir = os.path.join(FINAL_MODELS_DIR, MODEL_NAME)
    inner_dir = os.path.join(model_dir, MODEL_NAME)
    ensure_dir(inner_dir)
    
    # Copy assets
    src_img = os.path.join(DOWNLOADS_DIR, f"{MODEL_NAME}.png")
    src_mil = os.path.join(DOWNLOADS_DIR, f"{MODEL_NAME}_mil.png")
    src_glb = os.path.join(DOWNLOADS_DIR, f"{MODEL_NAME}_AI_Rodin.glb")
    
    if os.path.exists(src_img): shutil.copy2(src_img, os.path.join(inner_dir, f"{MODEL_NAME}.png"))
    if os.path.exists(src_mil): shutil.copy2(src_mil, os.path.join(inner_dir, f"{MODEL_NAME}_mil.png"))
    if os.path.exists(src_glb): shutil.copy2(src_glb, os.path.join(inner_dir, f"{MODEL_NAME}_AI_Rodin.glb"))
    
    # Create agent.json
    agent_data = {
        "name": MODEL_NAME,
        "readableName": READABLE_NAME,
        "type": "Missile",
        "modelUrlSlim": f"{MODEL_NAME}/{MODEL_NAME}_AI_Rodin.glb",
        "modelUrlFat": f"{MODEL_NAME}/{MODEL_NAME}_AI_Rodin.glb",
        "thumbnail": f"{MODEL_NAME}/{MODEL_NAME}.png",
        "mapIconUrl": f"{MODEL_NAME}/{MODEL_NAME}_mil.png",
        "dynamics": "BallisticMissileDynamics",
        "capabilities": ["Anti-Ballistic", "Anti-Satellite"]
    }
    
    with open(os.path.join(model_dir, "agent.json"), 'w', encoding='utf-8') as f:
        json.dump(agent_data, f, indent=2, ensure_ascii=False)
        
    # Zip
    zip_path = os.path.join(FINAL_MODELS_DIR, f"{MODEL_NAME}.zip")
    log.info(f"Zipping to {zip_path}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add agent.json
        zf.write(os.path.join(model_dir, "agent.json"), "agent.json")
        # Add assets
        for filename in os.listdir(inner_dir):
            zf.write(os.path.join(inner_dir, filename), f"{MODEL_NAME}/{filename}")
            
    log.info("Packaging complete!")
    return zip_path

if __name__ == "__main__":
    img_path = fetch_images()
    if img_path:
        generate_symbol()
        glb_path = generate_glb(img_path)
        if glb_path:
            package_model()
        else:
            log.info("GLB generation failed, skipping packaging.")
    else:
        log.info("Image fetch failed, aborting.")
