import os
import shutil
import zipfile

base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models"
src_png = os.path.join(base_dir, "downloads", "Su-33_Flanker-D.png")
dst_dir = os.path.join(base_dir, "Su-33_Flanker-D", "Su-33_Flanker-D")
dst_png = os.path.join(dst_dir, "Su-33_Flanker-D.png")

# Copy image
if os.path.exists(src_png):
    print(f"Copying {src_png} to {dst_png}")
    shutil.copy(src_png, dst_png)
else:
    print(f"Source image not found: {src_png}")

# Re-zip
zip_path = os.path.join(base_dir, "Su-33_Flanker-D.zip")
model_root = os.path.join(base_dir, "Su-33_Flanker-D")

print(f"Creating zip: {zip_path}")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add agent.json
    agent_json = os.path.join(model_root, "agent.json")
    if os.path.exists(agent_json):
        zipf.write(agent_json, arcname="agent.json")
    
    # Add assets
    assets_dir = os.path.join(model_root, "Su-33_Flanker-D")
    for root, _, files in os.walk(assets_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, model_root)
            zipf.write(file_path, arcname=rel_path)
            
print("Done.")
