import os
import sys
import requests
from PIL import Image
from io import BytesIO

print("Starting download_helper.py...")

# Proxy Configuration
PROXY_URL = "http://127.0.0.1:7897"
os.environ["HTTP_PROXY"] = PROXY_URL
os.environ["HTTPS_PROXY"] = PROXY_URL

DOWNLOADS_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\downloads"
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Mapping: Expected Filename (without ext) -> Image URL
TARGETS = {
    "J-20_Mighty_Dragon": "https://cdn.renderhub.com/netrunner-pl/chengdu-j-20-mighty-dragon-lowpoly-jet-fighter/chengdu-j-20-mighty-dragon-lowpoly-jet-fighter-01.jpg",
    "F-22_Raptor": "https://cdn.renderhub.com/netrunner-pl/lockheed-f-22-raptor-jet-fighter/lockheed-f-22-raptor-jet-fighter-01.jpg",
    "F-35_Lightning_II": "https://cdn.renderhub.com/netrunner-pl/lockheed-martin-f-35-lightning-ii/lockheed-martin-f-35-lightning-ii-01.jpg",
    "Su-57_Felon": "https://cdn.renderhub.com/netrunner-pl/sukhoi-su-57-felon-lowpoly-jet-fighter/sukhoi-su-57-felon-lowpoly-jet-fighter-01.jpg"
}

def download_and_process():
    for name, url in TARGETS.items():
        print(f"Processing {name} from {url}...")
        try:
            # 1. Download the image
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                print(f"  Failed to fetch image: {resp.status_code}")
                continue

            # 2. Open with PIL
            img = Image.open(BytesIO(resp.content))
            print(f"  Image opened. Format: {img.format}, Size: {img.size}")

            # 3. Convert to RGBA (for PNG transparency support if needed, though these are likely solid bg)
            # But we want to ensure it's saved as PNG
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            # 4. Save as PNG
            final_path = os.path.join(DOWNLOADS_DIR, f"{name}.png")
            img.save(final_path, "PNG")
            print(f"  Saved to {final_path}")

        except Exception as e:
            print(f"  Error processing {name}: {e}")

if __name__ == "__main__":
    download_and_process()
