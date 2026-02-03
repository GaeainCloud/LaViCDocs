import os
import military_symbol
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from PIL import Image, ImageDraw, ImageFont

# Config
MODEL_NAME = "道通龙鱼Dragonfish无人机"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "..", "models", MODEL_NAME, MODEL_NAME)

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_mil_symbol():
    print("Generating Military Symbol...")
    desc = "Friendly Fixed Wing Unmanned Aerial Vehicle"
    try:
        svg_string = military_symbol.get_symbol_svg_string_from_name(desc, style='light', bounding_padding=4, use_variants=True)
        
        svg_path = os.path.join(MODEL_DIR, f"{MODEL_NAME}_mil.svg")
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_string)
            
        png_path = os.path.join(MODEL_DIR, f"{MODEL_NAME}_mil.png")
        drawing = svg2rlg(svg_path)
        renderPM.drawToFile(drawing, png_path, fmt="PNG")
        print(f"Saved Military Symbol to {png_path}")
        
        # Cleanup SVG
        if os.path.exists(svg_path):
            os.remove(svg_path)
            
    except Exception as e:
        print(f"Error generating symbol: {e}")

def generate_placeholder_thumbnail():
    print("Generating Placeholder Thumbnail...")
    img = Image.new('RGB', (400, 300), color = (73, 109, 137))
    d = ImageDraw.Draw(img)
    # text = MODEL_NAME # PIL default font might not support Chinese
    text = "Dragonfish"
    
    # Draw text in center
    # d.text((10,10), text, fill=(255,255,0)) 
    # To center it properly without external fonts is tricky, just putting it roughly
    d.text((150, 140), text, fill=(255, 255, 255))
    
    png_path = os.path.join(MODEL_DIR, f"{MODEL_NAME}.png")
    img.save(png_path)
    print(f"Saved Thumbnail to {png_path}")

if __name__ == "__main__":
    ensure_dir(MODEL_DIR)
    generate_mil_symbol()
    generate_placeholder_thumbnail()
