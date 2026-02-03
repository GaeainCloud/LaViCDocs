import os
from PIL import Image

DOWNLOAD_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\downloads"

def convert_images():
    for filename in os.listdir(DOWNLOAD_DIR):
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        if os.path.isfile(file_path):
            try:
                img = Image.open(file_path)
                print(f"File: {filename}, Format: {img.format}, Mode: {img.mode}")
                
                # Convert to RGB and save as PNG
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                new_filename = os.path.splitext(filename)[0] + ".png"
                new_path = os.path.join(DOWNLOAD_DIR, new_filename)
                img.save(new_path, "PNG")
                print(f"Converted to: {new_filename}")
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    convert_images()
