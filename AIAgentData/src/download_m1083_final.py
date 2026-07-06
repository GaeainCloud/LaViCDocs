from logger import get_logger
log = get_logger(__name__)
import requests
from PIL import Image
from io import BytesIO

from config import DOWNLOADS_DIR, apply_proxy_env

apply_proxy_env()

URL_THUMB = "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/3%29_Oshkosh-produced_M1083_A1P2_5-ton_MTV_cargo_in_A-%3Dkit_configuration.jpg/1200px-3%29_Oshkosh-produced_M1083_A1P2_5-ton_MTV_cargo_in_A-%3Dkit_configuration.jpg"
URL_ORIG = "https://upload.wikimedia.org/wikipedia/commons/f/f7/3%29_Oshkosh-produced_M1083_A1P2_5-ton_MTV_cargo_in_A-%3Dkit_configuration.jpg"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
DEST_FILE = DOWNLOADS_DIR / "M1083_A1P2_Truck.png"


def download():
    for url in [URL_ORIG, URL_THUMB]:
        try:
            log.info(f"Trying {url}...")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                log.info(f"Failed with status {resp.status_code}")
                continue

            img = Image.open(BytesIO(resp.content))
            if img.mode != "RGB":
                img = img.convert("RGB")
            if img.width < 500:
                log.info(f"Image too small: {img.width}x{img.height}")
                continue
            img.save(DEST_FILE, "PNG")
            log.info(f"Success! Saved to {DEST_FILE} ({img.width}x{img.height})")
            return
        except Exception as e:
            log.info(f"Error: {e}")

    log.info("All downloads failed.")


if __name__ == "__main__":
    download()
