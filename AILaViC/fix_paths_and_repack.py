
import os
import zipfile

# Configuration
fixed_dir_name = "想定_防空反导-v1.60.9-修复版"
base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples"
fixed_dir_path = os.path.join(base_dir, fixed_dir_name)
json_path = os.path.join(fixed_dir_path, "simulation.json")
output_zip_path = os.path.join(base_dir, f"{fixed_dir_name}.zip")

# Path replacement config
wrong_prefix = "想定_防空反导-v1.60.9-修复版/"

def fix_json_paths():
    print(f"Reading {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if wrong prefix exists
    if wrong_prefix in content:
        print(f"Found occurrences of '{wrong_prefix}'. Removing it to match flat zip structure...")
        new_content = content.replace(wrong_prefix, "")
        
        print(f"Saving updated JSON to {json_path}...")
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("JSON paths update complete.")
    else:
        print(f"No occurrences of '{wrong_prefix}' found in JSON. Paths assume flat structure.")

def pack_zip():
    print(f"Creating ZIP archive at {output_zip_path}...")
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk relative to source_dir_path so files are at root of zip
        for root, dirs, files in os.walk(fixed_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate archive name relative to fixed_dir_path
                # This ensures simulation.json is at the root of the zip
                arcname = os.path.relpath(file_path, fixed_dir_path)
                print(f"  Adding {arcname}")
                zipf.write(file_path, arcname)
    print("ZIP creation complete.")

if __name__ == "__main__":
    fix_json_paths()
    pack_zip()
