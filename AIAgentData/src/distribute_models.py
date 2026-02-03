
import os
import shutil

base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models"
downloads_dir = os.path.join(base_dir, "downloads")

models = [
    "Dongfeng_Mengshi_CSK181",
    "Dongfeng-15_Missile_Launcher",
    "M1083_A1P2_Truck",
    "Norinco_Lynx_CS_VP4",
    "Oshkosh_JLTV",
    "Polaris_MRZR_Alpha"
]

for model in models:
    src_glb = os.path.join(downloads_dir, f"{model}_AI_Rodin.glb")
    dest_dir = os.path.join(base_dir, model, model)
    dest_glb = os.path.join(dest_dir, f"{model}_AI_Rodin.glb")
    
    if os.path.exists(src_glb):
        os.makedirs(dest_dir, exist_ok=True)
        print(f"Moving {src_glb} -> {dest_glb}")
        shutil.copy2(src_glb, dest_glb) # Copy instead of move to keep a backup
    else:
        print(f"Source not found: {src_glb}")

    # Also copy the PNG image
    src_png = os.path.join(downloads_dir, f"{model}.png")
    dest_png = os.path.join(dest_dir, f"{model}.png")
    if os.path.exists(src_png):
        print(f"Copying {src_png} -> {dest_png}")
        shutil.copy2(src_png, dest_png)
    else:
        print(f"PNG Source not found: {src_png}")
