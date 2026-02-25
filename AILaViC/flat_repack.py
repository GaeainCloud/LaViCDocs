
import os
import zipfile

# Config
base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples"
source_dir_name = "想定_防空反导-v1.60.9-修复版"
source_dir_path = os.path.join(base_dir, source_dir_name)
output_zip_path = os.path.join(base_dir, f"{source_dir_name}.zip")

def pack_zip():
    print(f"Zipping contents of {source_dir_path} directly to {output_zip_path}...")
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk relative to source_dir_path so files are at root of zip
        for root, dirs, files in os.walk(source_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate archive name relative to source_dir_path
                # This ensures simulation.json is at the root of the zip
                arcname = os.path.relpath(file_path, source_dir_path)
                print(f"  Adding {arcname}")
                zipf.write(file_path, arcname)
    print("Done.")

if __name__ == "__main__":
    pack_zip()
