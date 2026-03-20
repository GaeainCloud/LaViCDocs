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
from runtime_config import apply_proxy_env, get_models_dir

apply_proxy_env()
MODELS_DIR = get_models_dir()
ALLOW_PLACEHOLDER = os.getenv("AIALAVIC_ALLOW_PLACEHOLDER", "0") == "1"

# Drone Configuration
DRONE_CONFIGS = {
    "亿航EH216-S无人机": {
        "type": "multicopter",
        "urls": [
            "https://evtol.news/ehang-216/",
            "https://www.ehang.com/news/1190.html",
            "https://businessaviation.aero/directory/electrified-aircraft/all-electric-aircraft/all-electric-evtol/ehang-eh216-s"
        ]
    },
    "峰飞CarrayAll无人机": {
        "type": "fixed_wing_vtol",
        "urls": [
            "https://evtol.news/autoflight-carryall",
            "https://dronelife.com/2025/08/07/autoflight-delivers-worlds-first-one-ton-evtol-aircraft-with-full-airworthiness-certification/",
            "https://evtolinsights.com/autoflight-carryall-achieves-all-three-key-flight-approvals/"
        ]
    },
    "沃飞长空AE200": {
        "type": "fixed_wing_vtol",
        "urls": [
            "https://zgh.com/media-center/news/2025-09-29/?lang=en",
            "https://cnevpost.com/2025/09/30/geely-aerofugia-1st-ae200-100-evtol-off-line/",
            "https://aamnation.com/en/2025/10/08/aerofugia-begins-production-of-ae200-100-evtol-prototype/"
        ]
    },
    "纵横CW-15无人机": {
        "type": "fixed_wing_vtol",
        "urls": [
            "https://www.jouav.com/blog/long-range-drone.html",
            "https://www.jouav.com/products/cw-15.html",
            "https://www.jouav.com/vtol-drone"
        ]
    }
}

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def fetch_web_image(urls, drone_name_keywords):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    best_image = None
    max_score = 0
    
    for url in urls:
        print(f"[{drone_name_keywords[0]}] Scanning page: {url}")
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
                            
                    # print(f"  Found meta image ({meta_prop}): {img_url}")
                    
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
            # print(f"  Found {len(images)} images on page")
            
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
                
                # Keyword matching
                matched_keyword = False
                for keyword in drone_name_keywords:
                    if keyword.lower() in lower_src:
                        score += 50
                        matched_keyword = True
                        break
                
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

def generate_drone_glb(output_path, drone_type="multicopter"):
    print(f"Generating {drone_type} GLB model: {output_path}")
    
    # Colors
    dark_grey = [40, 40, 40, 255]
    black = [10, 10, 10, 255]
    light_grey = [150, 150, 150, 255] 
    white = [220, 220, 220, 255]
    
    parts = []
    
    # 1. Main Body (Fuselage)
    body = trimesh.creation.box(extents=[0.5, 0.25, 0.2])
    body.visual.face_colors = white
    parts.append(body)
    
    if drone_type == "fixed_wing_vtol":
        # Wings
        wing_span = 2.0
        wing_chord = 0.3
        wing_thickness = 0.05
        wing = trimesh.creation.box(extents=[wing_chord, wing_span, wing_thickness])
        wing.apply_translation([0, 0, 0.1]) # On top of body
        wing.visual.face_colors = white
        parts.append(wing)
        
        # Tail boom (Twin boom for many VTOLs like CW-15/CarryAll)
        boom_length = 1.2
        boom_radius = 0.03
        boom_offset = 0.5 # Distance from center
        
        for side in [-1, 1]:
            boom = trimesh.creation.cylinder(radius=boom_radius, height=boom_length)
            boom.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2, [0, 1, 0])) # Horizontal
            boom.apply_translation([0, side * boom_offset, 0])
            boom.visual.face_colors = dark_grey
            parts.append(boom)
            
            # VTOL Motors on booms (Front and Back)
            for end in [-1, 1]:
                motor_x = end * (boom_length/2 - 0.1)
                motor = trimesh.creation.cylinder(radius=0.04, height=0.1)
                motor.apply_translation([motor_x, side * boom_offset, 0.05])
                motor.visual.face_colors = black
                parts.append(motor)
                
                prop = trimesh.creation.cylinder(radius=0.25, height=0.01)
                prop.apply_translation([motor_x, side * boom_offset, 0.1])
                prop.visual.face_colors = light_grey
                parts.append(prop)
                
        # Tail stabilizer
        tail = trimesh.creation.box(extents=[0.2, 1.2, 0.02])
        tail.apply_translation([-boom_length/2, 0, 0.1])
        tail.visual.face_colors = white
        parts.append(tail)
        
    else: # multicopter (EH216 style - Coaxial 8 arms, 16 props, actually 8 arms with 2 motors each)
        # EH216 has 8 arms radiating from bottom
        arm_length = 0.6
        arm_thickness = 0.05
        
        for i in range(8):
            angle = i * (360/8)
            rad = math.radians(angle)
            
            # Arm
            arm = trimesh.creation.box(extents=[arm_length, arm_thickness, arm_thickness])
            rotation = trimesh.transformations.rotation_matrix(rad, [0, 0, 1])
            arm.apply_transform(rotation)
            arm.apply_translation([math.cos(rad)*(arm_length/2+0.2), math.sin(rad)*(arm_length/2+0.2), -0.1])
            arm.visual.face_colors = white
            parts.append(arm)
            
            # Motor/Prop Stack (Coaxial - Top and Bottom)
            end_x = math.cos(rad) * (arm_length + 0.2)
            end_y = math.sin(rad) * (arm_length + 0.2)
            
            for z_offset in [0.05, -0.05]:
                motor = trimesh.creation.cylinder(radius=0.05, height=0.05)
                motor.apply_translation([end_x, end_y, -0.1 + z_offset])
                motor.visual.face_colors = black
                parts.append(motor)
                
                prop = trimesh.creation.cylinder(radius=0.2, height=0.01)
                prop.apply_translation([end_x, end_y, -0.1 + z_offset * 1.5])
                prop.visual.face_colors = light_grey
                parts.append(prop)

    # Landing Gear (Skids)
    leg_height = 0.3
    skid_length = 0.5
    skid_offset_y = 0.2
    
    for side in [-1, 1]:
        leg = trimesh.creation.box(extents=[0.02, 0.02, leg_height])
        leg.apply_translation([0, side * skid_offset_y, -leg_height/2 - 0.1])
        leg.visual.face_colors = black
        parts.append(leg)
        
        skid = trimesh.creation.box(extents=[skid_length, 0.03, 0.03])
        skid.apply_translation([0, side * skid_offset_y, -leg_height - 0.1])
        skid.visual.face_colors = black
        parts.append(skid)
    
    # Combine all parts
    mesh = trimesh.util.concatenate(parts)
    
    mesh.export(output_path)
    return output_path

def process_drone(model_name, config):
    print(f"\nProcessing {model_name}...")
    model_dir = os.path.join(MODELS_DIR, model_name)
    assets_dir = os.path.join(model_dir, model_name)
    ensure_dir(assets_dir)
    agent_path = os.path.join(model_dir, "agent.json")
    
    # 1. Handle Image
    base_name = model_name
    png_filename = f"{base_name}.png"
    png_path = os.path.join(assets_dir, png_filename)
    
    # Search keywords derived from name or URL parts
    keywords = [base_name.split('无人机')[0], "drone", "evtol"]
    if "EH216" in base_name: keywords.insert(0, "EH216")
    if "CarrayAll" in base_name: keywords.insert(0, "CarryAll")
    if "AE200" in base_name: keywords.insert(0, "AE200")
    if "CW-15" in base_name: keywords.insert(0, "CW-15")
    
    image = fetch_web_image(config['urls'], keywords)
    if image is None:
        if not ALLOW_PLACEHOLDER:
            raise RuntimeError(
                f"Failed to fetch image for {base_name}. Set AIALAVIC_ALLOW_PLACEHOLDER=1 to allow placeholder output."
            )
        print("Failed to fetch real image, using placeholder.")
        image = generate_placeholder_image(base_name)
    
    # Convert to RGB and save as PNG
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(png_path, "PNG")
    print(f"Saved image to {png_path}")
    
    # 2. Handle GLB
    glb_filename = f"{base_name}_AI_Rodin.glb"
    glb_path = os.path.join(assets_dir, glb_filename)
    generate_drone_glb(glb_path, config['type'])
    print(f"Saved GLB to {glb_path}")
    
    # 3. Update JSON
    if os.path.exists(agent_path):
        with open(agent_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in {agent_path}")
                return

        # Handle list structure (single agent in list)
        is_list = isinstance(data, list)
        if is_list:
            if len(data) > 0:
                agent = data[0]
            else:
                print("Error: Empty list in JSON")
                return
        else:
            agent = data

        rel_png = f"{model_name}/{png_filename}"
        rel_glb = f"{model_name}/{glb_filename}"
        
        agent['modelUrlSymbols'] = [
            {
                "symbolSeries": 1,
                "symbolName": rel_png,
                "thumbnail": rel_png
            }
        ]
        agent['modelUrlSlim'] = rel_glb
        agent['modelUrlFat'] = rel_glb
        if "model" in agent:
            agent["model"]["modelName"] = agent.get("agentName", model_name)
            if "thumbnail" in agent["model"]:
                agent["model"]["thumbnail"]["url"] = rel_png
                agent["model"]["thumbnail"]["ossSig"] = png_filename
            if "dimModelUrls" in agent["model"] and agent["model"]["dimModelUrls"]:
                for dim in agent["model"]["dimModelUrls"]:
                    dim["url"] = rel_glb
                    dim["ossSig"] = glb_filename
        
        # Write back
        to_write = [agent] if is_list else agent
        
        with open(agent_path, 'w', encoding='utf-8') as f:
            json.dump(to_write, f, indent=2, ensure_ascii=False)
        print(f"Updated {agent_path}")
    else:
        print(f"Error: {agent_path} not found!")

def main():
    for model_name, config in DRONE_CONFIGS.items():
        try:
            process_drone(model_name, config)
        except Exception as e:
            print(f"Critical error processing {model_name}: {e}")

if __name__ == "__main__":
    main()
