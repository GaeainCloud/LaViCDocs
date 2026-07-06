from logger import get_logger
log = get_logger(__name__)
import requests
from PIL import Image
from io import BytesIO

from config import DOWNLOADS_DIR, apply_proxy_env

log.info("Starting download_helper.py...")
apply_proxy_env()

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Mapping: Expected Filename (without ext) -> Image URL
TARGETS = {
    "J-20_Mighty_Dragon": "https://cdn.renderhub.com/netrunner-pl/chengdu-j-20-mighty-dragon-lowpoly-jet-fighter/chengdu-j-20-mighty-dragon-lowpoly-jet-fighter-01.jpg",
    "F-22_Raptor": "https://cdn.renderhub.com/netrunner-pl/lockheed-f-22-raptor-jet-fighter/lockheed-f-22-raptor-jet-fighter-01.jpg",
    "F-35_Lightning_II": "https://cdn.renderhub.com/netrunner-pl/lockheed-martin-f-35-lightning-ii/lockheed-martin-f-35-lightning-ii-01.jpg",
    "Su-57_Felon": "https://cdn.renderhub.com/netrunner-pl/sukhoi-su-57-felon-lowpoly-jet-fighter/sukhoi-su-57-felon-lowpoly-jet-fighter-01.jpg",
}


def fetch_image_via_helper(model_name: str):
    """Return local PNG path if downloaded successfully, else None."""
    url = TARGETS.get(model_name)
    if not url:
        return None

    final_path = DOWNLOADS_DIR / f"{model_name}.png"
    if final_path.exists():
        return str(final_path)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return None

        img = Image.open(BytesIO(resp.content))
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        img.save(final_path, "PNG")
        return str(final_path)
    except Exception:
        return None


def download_and_process():
    for model_name in TARGETS:
        path = fetch_image_via_helper(model_name)
        if path:
            log.info(f"Saved: {path}")
        else:
            log.info(f"Failed: {model_name}")


if __name__ == "__main__":
    download_and_process()
