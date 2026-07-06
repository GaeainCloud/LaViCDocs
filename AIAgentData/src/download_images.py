from logger import get_logger
log = get_logger(__name__)
import requests
from PIL import Image, ImageDraw, ImageFont
import io

from config import DOWNLOADS_DIR, apply_proxy_env

apply_proxy_env()
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_URLS = {
    "J-35_Carrier_Variant": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/J-35_Zhuhai_2024.jpg/800px-J-35_Zhuhai_2024.jpg",
    "FA-18EF_Super_Hornet": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dc/FA-18_Super_Hornet_VFA-31.jpg/800px-FA-18_Super_Hornet_VFA-31.jpg",
    "Su-33_Flanker-D": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Su-33_Admiral_Kuznetsov.jpg/800px-Su-33_Admiral_Kuznetsov.jpg",
    "Rafale_M": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Rafale_M_-_RIAT_2009.jpg/800px-Rafale_M_-_RIAT_2009.jpg",
    "F-14D_Super_Tomcat": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/F-14A_Tomcat_VF-84.jpg/800px-F-14A_Tomcat_VF-84.jpg",
    "J-15_Flying_Shark": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/J-15_fighter.jpg/800px-J-15_fighter.jpg",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def generate_placeholder(name, save_path):
    log.info(f"Generating placeholder for {name}...")
    width, height = 800, 600
    img = Image.new("RGB", (width, height), (70, 130, 180))
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()

    text = name.replace("_", " ")
    d.text((50, 250), text, fill=(255, 255, 255), font=font)
    d.text((50, 320), "Placeholder Image", fill=(200, 200, 200), font=font)
    img.save(save_path, "PNG")


def download_image(url, save_path):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return False
        image = Image.open(io.BytesIO(response.content))
        image.save(save_path, "PNG")
        return True
    except Exception:
        return False


def main():
    for name, url in IMAGE_URLS.items():
        save_path = DOWNLOADS_DIR / f"{name}.png"
        if save_path.exists():
            log.info(f"Image already exists: {save_path}")
            continue

        if not (url and download_image(url, save_path)):
            generate_placeholder(name, save_path)


if __name__ == "__main__":
    main()
