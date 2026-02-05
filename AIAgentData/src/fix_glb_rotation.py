import trimesh
import os
import numpy as np

# Use raw string for Windows path
BASE_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData"
MODELS_DIR = os.path.join(BASE_DIR, "models")
DOWNLOADS_DIR = os.path.join(MODELS_DIR, "downloads")

MODELS = [
    "J-20_Mighty_Dragon",
    "F-22_Raptor",
    "F-35_Lightning_II",
    "Su-57_Felon"
]

def rotate_glb(model_name):
    # Source from downloads (Clean original from Rodin/Cache)
    src_path = os.path.join(DOWNLOADS_DIR, f"{model_name}_AI_Rodin.glb")
    # Target in models folder
    dst_path = os.path.join(MODELS_DIR, model_name, model_name, f"{model_name}_AI_Rodin.glb")
    
    # If source doesn't exist, check if target exists and use it (warning: might be double rotated if we aren't careful, but we assume downloads has originals)
    if not os.path.exists(src_path):
        print(f"[Warning] Source not found at {src_path}")
        if os.path.exists(dst_path):
            print(f"  Fallback: Using existing target {dst_path} (Risk of double rotation!)")
            src_path = dst_path
        else:
            print(f"  Skipping {model_name}: No file found.")
            return

    print(f"Processing {model_name}...")
    try:
        # Load
        scene = trimesh.load(src_path, force='scene')
        
        # 1. Rotate -90 around X (Z-up to Y-up)
        # Matrix: [[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]]
        rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
        scene.apply_transform(rot_x)
        
        # 2. Rotate 180 around Y (Facing Correction in Y-up system)
        # Vertical axis in Y-up is Y.
        rot_y = trimesh.transformations.rotation_matrix(np.radians(180), [0, 1, 0])
        scene.apply_transform(rot_y)
        
        # Ensure target dir exists
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        # Export
        data = trimesh.exchange.gltf.export_glb(scene)
        with open(dst_path, 'wb') as f:
            f.write(data)
        print(f"  Saved to {dst_path}")
        
    except Exception as e:
        print(f"  Error: {e}")

def main():
    for m in MODELS:
        rotate_glb(m)

if __name__ == "__main__":
    main()
