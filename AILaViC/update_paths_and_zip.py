
import json
import os
import zipfile
import shutil

# Configuration
fixed_dir_name = "想定_防空反导-v1.60.9-修复版"
base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples"
fixed_dir_path = os.path.join(base_dir, fixed_dir_name)
json_path = os.path.join(fixed_dir_path, "simulation.json")
output_zip_path = os.path.join(base_dir, f"{fixed_dir_name}.zip")

# Path replacement config
old_path_prefix = "想定_防空反导-v1.60.9-null-2026年02月10日07时01分46秒"
new_path_prefix = "想定_防空反导-v1.60.9-修复版"

def update_json_paths():
    print(f"Reading {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if old path exists
    if old_path_prefix in content:
        print(f"Found occurrences of '{old_path_prefix}'. Replacing with '{new_path_prefix}'...")
        new_content = content.replace(old_path_prefix, new_path_prefix)
        
        print(f"Saving updated JSON to {json_path}...")
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("JSON paths update complete.")
        return True
    else:
        print(f"No occurrences of '{old_path_prefix}' found in JSON.")
        return True # Proceed anyway

def pack_zip():
    print(f"Creating ZIP archive at {output_zip_path}...")
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through the fixed directory and add files
        root_len = len(base_dir)
        
        for root, dirs, files in os.walk(fixed_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                # arcname should include the folder name "想定_防空反导-v1.60.9-修复版"
                arcname = file_path[root_len:].lstrip(os.sep)
                print(f"  Adding {arcname}")
                zipf.write(file_path, arcname)
                
    print("ZIP creation complete.")

if __name__ == "__main__":
    if update_json_paths():
        pack_zip()
