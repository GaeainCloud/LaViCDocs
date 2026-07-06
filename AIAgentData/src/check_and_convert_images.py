from pathlib import Path

from config import DOWNLOADS_DIR
from logger import get_logger
from utils.image_utils import convert_to_rgb_png

log = get_logger(__name__)

def convert_images(download_dir=None):
    download_dir = Path(download_dir) if download_dir else DOWNLOADS_DIR

    for file_path in download_dir.iterdir():
        if file_path.is_file():
            png_path = file_path.with_suffix(".png")
            # [P2-2] 跳过已经是 PNG 的文件，避免无意义的自转换
            if file_path.suffix.lower() == ".png":
                continue
            convert_to_rgb_png(file_path, png_path)

if __name__ == "__main__":
    convert_images()
