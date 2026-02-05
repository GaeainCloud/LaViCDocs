import os
import requests
from PIL import Image, ImageDraw, ImageFont
import io

# Configuration
BASE_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData"
DOWNLOADS_DIR = os.path.join(BASE_DIR, "models", "downloads")

# Ensure directory exists
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

# Model Mapping (Name -> URL)
# Using Wikimedia Commons or similar reliable sources where possible.
# If URL is None or fails, a placeholder will be generated.
IMAGE_URLS = {
    "J-35_Carrier_Variant": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/J-35_Zhuhai_2024.jpg/800px-J-35_Zhuhai_2024.jpg", # Likely to fail or be 404, will fallback
    "FA-18EF_Super_Hornet": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dc/FA-18_Super_Hornet_VFA-31.jpg/800px-FA-18_Super_Hornet_VFA-31.jpg",
    "Su-33_Flanker-D": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Su-33_Admiral_Kuznetsov.jpg/800px-Su-33_Admiral_Kuznetsov.jpg",
    "Rafale_M": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Rafale_M_-_RIAT_2009.jpg/800px-Rafale_M_-_RIAT_2009.jpg",
    "F-14D_Super_Tomcat": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/F-14A_Tomcat_VF-84.jpg/800px-F-14A_Tomcat_VF-84.jpg",
    "J-15_Flying_Shark": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/J-15_fighter.jpg/800px-J-15_fighter.jpg" # Might fail
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def generate_placeholder(name, save_path):
    print(f"Generating placeholder for {name}...")
    width, height = 800, 600
    color = (70, 130, 180) # SteelBlue
    img = Image.new('RGB', (width, height), color)
    d = ImageDraw.Draw(img)
    
    try:
        # Try to load a font, otherwise use default
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
        
    text = name.replace("_", " ")
    # Calculate text position (approximate centering)
    # text_width = d.textlength(text, font=font) # Pillow 9.2+
    # x = (width - text_width) / 2
    # y = height / 2
    d.text((50, 250), text, fill=(255, 255, 255), font=font)
    d.text((50, 320), "Placeholder Image", fill=(200, 200, 200), font=font)
    
    img.save(save_path, "PNG")
    print(f"Saved placeholder to {save_path}")

def download_image(url, save_path):
    print(f"Downloading {url}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            image_data = response.content
            image = Image.open(io.BytesIO(image_data))
            image.save(save_path, "PNG")
            print(f"Successfully downloaded and saved to {save_path}")
            return True
        else:
            print(f"Failed to download (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"Error downloading: {e}")
        return False

def main():
    for name, url in IMAGE_URLS.items():
        save_path = os.path.join(DOWNLOADS_DIR, f"{name}.png")
        
        if os.path.exists(save_path):
            print(f"Image already exists: {save_path}")
            continue
            
        success = False
        if url:
            success = download_image(url, save_path)
            
        if not success:
            generate_placeholder(name, save_path)

if __name__ == "__main__":
    main()
