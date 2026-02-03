import os
import json
import requests
import time
import shutil
import zipfile
from bs4 import BeautifulSoup
from PIL import Image
import military_symbol
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# --- Configuration ---
MODEL_NAME = "RIM-161_SM-3"
READABLE_NAME = "RIM-161 Standard Missile 3"
SYMBOL_DESC = "Friendly Air Defense Missile" # Or "Friendly Missile"
DOWNLOADS_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\downloads"
FINAL_MODELS_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models"
RODIN_API_KEY = "k9TcfFoEhNd9cCPP2guHAHHHkctZHIRhZDywZ1euGUXwihbYLpOjQhofby80NJez"

# Proxy Config
PROXY_URL = "http://127.0.0.1:7897"
os.environ["HTTP_PROXY"] = PROXY_URL
os.environ["HTTPS_PROXY"] = PROXY_URL

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
    print(f"Fetching images for {MODEL_NAME}...")
    ensure_dir(DOWNLOADS_DIR)
    
    candidates = []
    
    # Add direct URLs first
    for url in IMAGE_URLS:
        if url.lower().endswith(('.jpg', '.png', '.jpeg')):
            candidates.append(url)

    # Scrape others
    for url in IMAGE_URLS:
        if url in candidates: continue
        try:
            print(f"Scraping {url}...")
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                # Try og:image
                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"):
                    candidates.append(og_img["content"])
                
                # Find other large images
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src and src.startswith('http') and ('jpg' in src or 'png' in src):
                        candidates.append(src)
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    # Download and select best
    best_image_path = os.path.join(DOWNLOADS_DIR, f"{MODEL_NAME}.png")
    best_size = 0
    
    for i, url in enumerate(candidates[:10]): # Limit to 10
        try:
            print(f"Checking image {i}: {url}")
            r = requests.get(url, headers=HEADERS, timeout=10, stream=True)
            if r.status_code == 200:
                # Save to temp
                temp_path = os.path.join(DOWNLOADS_DIR, f"temp_{i}.png")
                with open(temp_path, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)
                
                # Check size/resolution
                try:
                    with Image.open(temp_path) as img:
                        width, height = img.size
                        size = os.path.getsize(temp_path)
                        
                        print(f"  Size: {width}x{height}, Bytes: {size}")
                        
                        # Criteria: > 400px, prefer larger but not huge
                        score = width * height
                        if width > 400 and height > 400:
                            if score > best_size:
                                best_size = score
                                # Convert to PNG and save as best
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                img.save(best_image_path, "PNG")
                                print(f"  -> New Best Image selected")
                except Exception as e:
                    print(f"  Invalid image: {e}")
                
                # Cleanup temp
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            print(f"Failed to download {url}: {e}")

    if os.path.exists(best_image_path):
        print(f"Final image saved to {best_image_path}")
        return best_image_path
    else:
        print("Failed to find any suitable image.")
        return None

# --- 2. Generate Military Symbol ---
def generate_symbol():
    print(f"Generating military symbol for {SYMBOL_DESC}...")
    try:
        svg_string = military_symbol.get_symbol_svg_string_from_name(SYMBOL_DESC, style='light', bounding_padding=4, use_variants=True)
        if not svg_string:
            print("Failed to generate SVG string.")
            return None
            
        svg_path = os.path.join(DOWNLOADS_DIR, f"{MODEL_NAME}_mil.svg")
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_string)
            
        png_path = os.path.join(DOWNLOADS_DIR, f"{MODEL_NAME}_mil.png")
        drawing = svg2rlg(svg_path)
        renderPM.drawToFile(drawing, png_path, fmt="PNG")
        print(f"Symbol saved to {png_path}")
        return png_path
    except Exception as e:
        print(f"Error generating symbol: {e}")
        return None

# --- 3. Generate GLB (Rodin) ---
def generate_glb(image_path):
    print("Generating 3D model with Rodin...")
    if not image_path or not os.path.exists(image_path):
        print("No input image for Rodin.")
        return None
        
    output_glb = os.path.join(DOWNLOADS_DIR, f"{MODEL_NAME}_AI_Rodin.glb")
    # If already exists, skip (for testing)
    # if os.path.exists(output_glb): return output_glb
    
    headers = {
        "Authorization": f"Bearer {RODIN_API_KEY}",
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
        
        print("Posting job to Rodin...")
        resp = requests.post("https://hyperhuman.deemos.com/api/v2/rodin", headers=headers, files=files)
        if resp.status_code not in [200, 201]:
            print(f"Rodin Create Failed: {resp.text}")
            return None
            
        data = resp.json()
        uuid = data.get("uuid")
        sub_key = data.get("jobs", {}).get("subscription_key") or data.get("subscription_key")
        
        if not uuid or not sub_key:
            print("Failed to get UUID or Subscription Key")
            return None
            
        print(f"Job started. UUID: {uuid}")
        
        # Poll
        while True:
            time.sleep(5)
            r_status = requests.post("https://hyperhuman.deemos.com/api/v2/status", headers=headers, json={"subscription_key": sub_key})
            if r_status.status_code != 200:
                print("Polling error")
                continue
                
            s_data = r_status.json()
            jobs = s_data.get("jobs", [])
            statuses = [j["status"] for j in jobs]
            print(f"Status: {statuses}")
            
            if all(s == "Done" for s in statuses):
                break
            if any(s == "Failed" for s in statuses):
                print("Rodin Job Failed")
                return None
                
        # Download
        print("Downloading result...")
        r_down = requests.post("https://hyperhuman.deemos.com/api/v2/download", headers=headers, json={'task_uuid': uuid})
        if r_down.status_code != 200:
            print("Download init failed")
            return None
            
        d_data = r_down.json()
        glb_url = None
        for item in d_data.get("list", []):
            if item["name"].endswith(".glb"):
                glb_url = item["url"]
                break
                
        if glb_url:
            print(f"Downloading GLB from {glb_url}...")
            r_glb = requests.get(glb_url, stream=True)
            with open(output_glb, 'wb') as f:
                shutil.copyfileobj(r_glb.raw, f)
            print(f"GLB saved to {output_glb}")
            return output_glb
            
    except Exception as e:
        print(f"Rodin error: {e}")
        return None

# --- 4. Package ---
def package_model():
    print("Packaging model...")
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
    print(f"Zipping to {zip_path}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add agent.json
        zf.write(os.path.join(model_dir, "agent.json"), "agent.json")
        # Add assets
        for filename in os.listdir(inner_dir):
            zf.write(os.path.join(inner_dir, filename), f"{MODEL_NAME}/{filename}")
            
    print("Packaging complete!")
    return zip_path

if __name__ == "__main__":
    img_path = fetch_images()
    if img_path:
        generate_symbol()
        glb_path = generate_glb(img_path)
        if glb_path:
            package_model()
        else:
            print("GLB generation failed, skipping packaging.")
    else:
        print("Image fetch failed, aborting.")
