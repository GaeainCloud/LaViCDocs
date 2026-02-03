import os
import shutil

base_dir = r"D:\AIProduct\GAEALaViC\AIAgentData\models"
old_name = "纵横CW-15"
new_name = "纵横CW-15无人机"

old_path = os.path.join(base_dir, old_name)
new_path = os.path.join(base_dir, new_name)

if os.path.exists(old_path):
    print(f"Renaming {old_path} to {new_path}")
    os.rename(old_path, new_path)
    
    # Rename subfolder
    old_sub = os.path.join(new_path, old_name)
    new_sub = os.path.join(new_path, new_name)
    if os.path.exists(old_sub):
        print(f"Renaming subfolder {old_sub} to {new_sub}")
        os.rename(old_sub, new_sub)
        
        # Rename files inside
        for filename in os.listdir(new_sub):
            if old_name in filename:
                # Be careful not to double replace if "无人机" is already there (like in the GLB)
                # But here we are replacing "纵横CW-15" with "纵横CW-15无人机"
                # If filename is "纵横CW-15无人机_AI_Rodin.glb", replacing "纵横CW-15" gives "纵横CW-15无人机无人机_AI_Rodin.glb" -> WRONG.
                
                # Check strict start match to avoid double replacement
                if filename.startswith(old_name) and not filename.startswith(new_name):
                    new_filename = filename.replace(old_name, new_name, 1)
                    print(f"Renaming file {filename} to {new_filename}")
                    os.rename(os.path.join(new_sub, filename), os.path.join(new_sub, new_filename))

    # Remove old zip if exists
    old_zip = os.path.join(base_dir, f"{old_name}.zip")
    if os.path.exists(old_zip):
        os.remove(old_zip)
        print(f"Removed old zip {old_zip}")

else:
    print(f"Directory {old_path} not found. checking if already renamed.")
    if os.path.exists(new_path):
        print(f"Directory {new_path} already exists.")
