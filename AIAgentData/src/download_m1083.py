from logger import get_logger
log = get_logger(__name__)
import hashlib
import requests

from config import DOWNLOADS_DIR, apply_proxy_env

apply_proxy_env()


def get_wikimedia_url(filename):
    filename = filename.replace(" ", "_")
    m = hashlib.md5(filename.encode("utf-8")).hexdigest()
    return f"https://upload.wikimedia.org/wikipedia/commons/{m[0]}/{m[:2]}/{filename}"


def download_file():
    filename = "M1083_MTV.png"
    url = get_wikimedia_url(filename)
    output_path = DOWNLOADS_DIR / "M1083_A1P2_Truck.png"

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            output_path.write_bytes(resp.content)
            log.info("Download success!")
            return

        backup_url = "http://www.military-today.com/trucks/m1083_fmtv.jpg"
        resp = requests.get(backup_url, headers=headers, timeout=20)
        if resp.status_code == 200:
            output_path.write_bytes(resp.content)
            log.info("Download success (backup)!")
        else:
            log.info(f"Backup failed: {resp.status_code}")
    except Exception as e:
        log.info(f"Error: {e}")


if __name__ == "__main__":
    download_file()
