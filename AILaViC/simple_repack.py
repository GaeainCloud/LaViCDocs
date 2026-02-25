
import os
import zipfile

# Config
base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples"
source_dir_name = "想定_防空反导-v1.60.9-修复版"
source_dir_path = os.path.join(base_dir, source_dir_name)
output_zip_path = os.path.join(base_dir, f"{source_dir_name}.zip")

def pack_zip():
    print(f"Zipping {source_dir_path} to {output_zip_path}...")
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # We want the zip to contain the folder "想定_防空反导-v1.60.9-修复版"
        # So we walk relative to base_dir, but only inside source_dir_name
        
        # Walk the source directory
        for root, dirs, files in os.walk(source_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate archive name relative to base_dir
                # base_dir is .../examples
                # file_path is .../examples/想定_防空反导-v1.60.9-修复版/...
                # arcname should be 想定_防空反导-v1.60.9-修复版/...
                arcname = os.path.relpath(file_path, base_dir)
                print(f"  Adding {arcname}")
                zipf.write(file_path, arcname)
    print("Done.")

if __name__ == "__main__":
    pack_zip()
