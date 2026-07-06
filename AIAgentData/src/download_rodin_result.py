from logger import get_logger
log = get_logger(__name__)
import requests
import os

from config import DOWNLOADS_DIR, apply_proxy_env, require_rodin_api_key

apply_proxy_env()

API_KEY = require_rodin_api_key()
OUTPUT_GLB = str(DOWNLOADS_DIR / "M1083_A1P2_Truck_AI_Rodin.glb")
TASK_UUID = "8de7952e-49c8-44d3-b22b-6cb698bf1460"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "User-Agent": "blender-mcp"
}

def download_asset(task_uuid):
    log.info(f"Downloading asset {task_uuid}...")
    try:
        response = requests.post(
            "https://hyperhuman.deemos.com/api/v2/download",
            headers=HEADERS,
            json={'task_uuid': task_uuid}
        )
        log.info(f"Download response code: {response.status_code}")
        
        if response.status_code not in [200, 201]:
            log.info(f"Download init failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        glb_url = None
        for item in data.get("list", []):
            if item["name"].endswith(".glb"):
                glb_url = item["url"]
                break
        
        if not glb_url:
            log.info("No GLB found in download list.")
            return False
            
        log.info(f"Downloading GLB from {glb_url}...")
        glb_resp = requests.get(glb_url, stream=True)
        if glb_resp.status_code == 200:
            with open(OUTPUT_GLB, 'wb') as f:
                for chunk in glb_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            log.info(f"Saved to {OUTPUT_GLB}")
            return True
        else:
            log.info(f"GLB download failed: {glb_resp.status_code}")
            return False
            
    except Exception as e:
        log.info(f"Error downloading: {e}")
        return False

if __name__ == "__main__":
    download_asset(TASK_UUID)
