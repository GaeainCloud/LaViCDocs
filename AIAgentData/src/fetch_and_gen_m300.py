import os
import json
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import trimesh
import numpy as np
import random
import math

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "..", "models")
ASSETS_DIR = os.path.join(MODELS_DIR, "assets")
AGENT_FILE = "大疆Matrice 300RTK无人机.json"
AGENT_PATH = os.path.join(MODELS_DIR, AGENT_FILE)
# List of URLs to search for images (Third-party retailers/reviews, avoiding official site search)
TARGET_URLS = [
    "https://www.genpacdrones.com/product/dji-matrice-300-rtk-drone/",
    "https://www.heliguy.com/products/matrice-300-rtk",
    "https://enterpriseuav.co.uk/dji-matrice-300-rtk/"
]

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def fetch_web_image(urls):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    best_image = None
    max_score = 0
    
    for url in urls:
        print(f"Scanning page: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"  Status {response.status_code} for {url}")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Check Meta Tags (og:image, twitter:image) - High Priority
            for meta_prop in ["og:image", "twitter:image"]:
                meta_tag = soup.find("meta", property=meta_prop) or soup.find("meta", attrs={"name": meta_prop})
                if meta_tag and meta_tag.get("content"):
                    img_url = meta_tag["content"]
                    if not img_url.startswith('http'):
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            base_url = '/'.join(url.split('/')[:3])
                            img_url = base_url + img_url
                            
                    print(f"  Found meta image ({meta_prop}): {img_url}")
                    
                    # Basic validation for meta image
                    if any(x in img_url.lower() for x in ['logo', 'icon', 'avatar']):
                        continue
                        
                    # Give meta images a high initial score
                    score = 80
                    if img_url != best_image:
                         if score > max_score:
                             max_score = score
                             best_image = img_url

            # 2. Check Page Images
            images = soup.find_all('img')
            print(f"  Found {len(images)} images on page")
            
            for img in images:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if not src:
                    continue
                
                # Fix relative URLs
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    base_url = '/'.join(url.split('/')[:3])
                    src = base_url + src
                elif not src.startswith('http'):
                    continue
                
                # Filter out obvious bad candidates
                lower_src = src.lower()
                if any(x in lower_src for x in ['icon', 'logo', 'svg', 'avatar', 'button', 'cart', 'payment', 'facebook', 'twitter', 'instagram']):
                    continue
                if not any(x in lower_src for x in ['jpg', 'png', 'jpeg', 'webp']):
                    continue
                
                # Scoring system
                score = 0
                if 'matrice' in lower_src or 'm300' in lower_src:
                    score += 50
                if 'product' in lower_src:
                    score += 20
                if 'gallery' in lower_src or 'large' in lower_src:
                    score += 15
                if 'aircraft' in lower_src or 'drone' in lower_src:
                    score += 10
                
                # Heuristic for product shots
                width = img.get('width')
                height = img.get('height')
                if width and height:
                    try:
                        w, h = int(width), int(height)
                        if w < 400 or h < 400: # Increase min size to avoid thumbnails
                            continue
                        if w > 800:
                            score += 10
                    except:
                        pass
                
                if score > max_score:
                    try:
                        # Verify image content length/size
                        head = requests.head(src, headers=headers, timeout=5)
                        if 'content-length' in head.headers:
                            size = int(head.headers['content-length'])
                            if size < 30000: # Filter small images < 30KB
                                continue
                        
                        print(f"  New best candidate (score {score}): {src}")
                        max_score = score
                        best_image = src
                    except:
                        continue
                        
        except Exception as e:
            print(f"Error scanning {url}: {e}")
            
    if best_image:
        print(f"Downloading best match: {best_image}")
        try:
            resp = requests.get(best_image, headers=headers, timeout=15)
            img = Image.open(BytesIO(resp.content))
            return img
        except Exception as e:
            print(f"Failed to download {best_image}: {e}")

    return None

def generate_placeholder_image(text):
    print("Generating placeholder image...")
    width, height = 512, 512
    color = (50, 50, 50)
    image = Image.new('RGB', (width, height), color=color)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
    
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    position = ((width - text_width) / 2, (height - text_height) / 2)
    draw.text(position, text, fill=(255, 255, 255), font=font)
    return image

def generate_drone_glb(filename):
    print("Generating M300-style drone GLB model...")
    
    # Colors
    dark_grey = [40, 40, 40, 255]
    black = [10, 10, 10, 255]
    light_grey = [150, 150, 150, 255] # Props
    
    parts = []
    
    # 1. Main Body (Central Hub) - slightly elongated box
    body = trimesh.creation.box(extents=[0.3, 0.2, 0.15])
    body.visual.face_colors = dark_grey
    parts.append(body)
    
    # 2. Arms (M300 has inverted props, arms go slightly up then down or straight)
    # We'll do 4 arms extending from corners
    arm_length = 0.4
    arm_thickness = 0.04
    
    # Angles for 4 arms (X config)
    angles = [45, 135, 225, 315]
    
    for angle in angles:
        rad = math.radians(angle)
        x = math.cos(rad) * (arm_length / 2 + 0.1) # Offset from center
        y = math.sin(rad) * (arm_length / 2 + 0.1)
        
        # Arm strut
        arm = trimesh.creation.box(extents=[arm_length, arm_thickness, arm_thickness])
        # Rotate arm to match angle
        rotation = trimesh.transformations.rotation_matrix(rad, [0, 0, 1])
        arm.apply_transform(rotation)
        # Translate to position
        arm.apply_translation([x, y, 0])
        arm.visual.face_colors = dark_grey
        parts.append(arm)
        
        # Motor housing (at end of arm)
        end_x = math.cos(rad) * (arm_length + 0.1)
        end_y = math.sin(rad) * (arm_length + 0.1)
        
        motor = trimesh.creation.cylinder(radius=0.04, height=0.08)
        # M300 motors face DOWN usually, but let's put them standard for simplicity or check M300 ref.
        # M300 props are inverted (below the arm).
        motor.apply_translation([end_x, end_y, -0.05])
        motor.visual.face_colors = black
        parts.append(motor)
        
        # Propeller (below motor)
        prop = trimesh.creation.cylinder(radius=0.25, height=0.01)
        prop.apply_translation([end_x, end_y, -0.1])
        prop.visual.face_colors = light_grey
        parts.append(prop)

    # 3. Landing Gear (Skids)
    # Two legs going down, then horizontal skids
    leg_height = 0.25
    skid_length = 0.4
    skid_offset_y = 0.15 # Distance from center line
    
    for side in [-1, 1]: # Left and Right
        # Vertical Leg
        leg = trimesh.creation.box(extents=[0.02, 0.02, leg_height])
        leg.apply_translation([0, side * skid_offset_y, -leg_height/2])
        leg.visual.face_colors = black
        parts.append(leg)
        
        # Horizontal Skid
        skid = trimesh.creation.box(extents=[skid_length, 0.03, 0.03])
        skid.apply_translation([0, side * skid_offset_y, -leg_height])
        skid.visual.face_colors = black
        parts.append(skid)
    
    # Combine all parts
    mesh = trimesh.util.concatenate(parts)
    
    path = os.path.join(ASSETS_DIR, filename)
    mesh.export(path)
    return path

def main():
    ensure_dir(ASSETS_DIR)
    
    # 1. Handle Image
    base_name = "大疆Matrice 300RTK无人机"
    png_filename = f"{base_name}.png"
    png_path = os.path.join(ASSETS_DIR, png_filename)
    
    image = fetch_web_image(TARGET_URLS)
    if image is None:
        print("Failed to fetch real image, using placeholder.")
        image = generate_placeholder_image(base_name)
    
    # Convert to RGB and save as PNG
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(png_path, "PNG")
    print(f"Saved image to {png_path}")
    
    # 2. Handle GLB
    glb_filename = f"{base_name}.glb"
    generate_drone_glb(glb_filename)
    print(f"Saved GLB to {os.path.join(ASSETS_DIR, glb_filename)}")
    
    # 3. Update JSON
    if os.path.exists(AGENT_PATH):
        with open(AGENT_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle list structure (single agent in list)
        if isinstance(data, list):
            if len(data) > 0:
                agent = data[0]
            else:
                print("Error: Empty list in JSON")
                return
        else:
            agent = data

        rel_png = f"assets/{png_filename}"
        rel_glb = f"assets/{glb_filename}"
        
        agent['modelUrlSymbols'] = [
            {
                "symbolSeries": 1,
                "symbolName": rel_png,
                "thumbnail": rel_png
            }
        ]
        agent['modelUrlSlim'] = rel_glb
        agent['modelUrlFat'] = rel_glb
        
        with open(AGENT_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated {AGENT_FILE}")
    else:
        print(f"Error: {AGENT_FILE} not found!")

if __name__ == "__main__":
    main()
