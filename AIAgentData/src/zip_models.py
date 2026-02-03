import os
import zipfile

def zip_model_folders(models_dir):
    # Get all subdirectories in the models folder
    try:
        items = os.listdir(models_dir)
    except FileNotFoundError:
        print(f"Error: Directory not found: {models_dir}")
        return

    dirs = [d for d in items if os.path.isdir(os.path.join(models_dir, d)) and d != "assets"]

    print(f"Found directories to zip: {dirs}")

    for folder_name in dirs:
        folder_path = os.path.join(models_dir, folder_name)
        zip_path = os.path.join(models_dir, f"{folder_name}.zip")
        
        print(f"Zipping {folder_name} to {zip_path}...")
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Calculate the archive name (relative path inside the zip)
                        # We want the content to be at the root of the zip (no top-level folder)
                        rel_path = os.path.relpath(file_path, folder_path)
                        
                        # Python's zipfile writes filenames in UTF-8 by default if they contain non-ASCII
                        zipf.write(file_path, arcname=rel_path)
            print(f"Successfully created {zip_path}")
        except Exception as e:
            print(f"Failed to zip {folder_name}: {e}")

if __name__ == "__main__":
    print(f"Running zip_models.py from {__file__}")
    # base_dir = r"D:\AIProduct\GAEALaViC\AIAgentData\models"
    base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models"
    print(f"Base dir is: {base_dir}")
    zip_model_folders(base_dir)
