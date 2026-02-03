import requests
from PIL import Image
from io import BytesIO
import os

URL_THUMB = "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/3%29_Oshkosh-produced_M1083_A1P2_5-ton_MTV_cargo_in_A-%3Dkit_configuration.jpg/1200px-3%29_Oshkosh-produced_M1083_A1P2_5-ton_MTV_cargo_in_A-%3Dkit_configuration.jpg"
URL_ORIG = "https://upload.wikimedia.org/wikipedia/commons/f/f7/3%29_Oshkosh-produced_M1083_A1P2_5-ton_MTV_cargo_in_A-%3Dkit_configuration.jpg"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

DEST_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\downloads"
os.makedirs(DEST_DIR, exist_ok=True)
DEST_FILE = os.path.join(DEST_DIR, "M1083_A1P2_Truck.png")

def download():
    for url in [URL_ORIG, URL_THUMB]:
        try:
            print(f"Trying {url}...")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Check resolution
                if img.width < 500:
                    print(f"Image too small: {img.width}x{img.height}")
                    continue
                    
                img.save(DEST_FILE, "PNG")
                print(f"Success! Saved to {DEST_FILE} ({img.width}x{img.height})")
                return
            else:
                print(f"Failed with status {resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("All downloads failed.")

if __name__ == "__main__":
    download()
