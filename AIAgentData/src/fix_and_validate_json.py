import json
import zipfile
import os
import shutil

MODELS_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models"
PACKAGES = [
    "J-20_Mighty_Dragon",
    "F-22_Raptor",
    "F-35_Lightning_II",
    "Su-57_Felon"
]

REQUIRED_FIELDS = ["agentName", "agentDesc", "modelUrlSlim", "modelUrlFat", "thumbnail", "modelUrlSymbols", "missionableDynamics"]

def fix_and_validate():
    for pkg_name in PACKAGES:
        zip_path = os.path.join(MODELS_DIR, f"{pkg_name}.zip")
        print(f"Processing {zip_path}...")
        
        if not os.path.exists(zip_path):
            print(f"  Error: File not found!")
            continue

        try:
            # Read existing content
            with zipfile.ZipFile(zip_path, 'r') as zin:
                content = zin.read("agent.json")
                data = json.loads(content)
                
                # Check other files existence
                file_list = zin.namelist()
                print(f"  Files in zip: {file_list}")

            # Fix structure if needed
            is_fixed = False
            if isinstance(data, dict):
                print("  Detecting dict, wrapping in list...")
                data = [data]
                is_fixed = True
            elif isinstance(data, list):
                print("  Already a list.")
            else:
                print(f"  Unknown type: {type(data)}")
                continue

            # Validate Content
            agent = data[0]
            missing = [field for field in REQUIRED_FIELDS if field not in agent]
            if missing:
                print(f"  Error: Missing fields: {missing}")
            else:
                print("  Structure validation passed.")

            # Validate Assets references
            # Expected paths in zip: "{pkg_name}/{filename}"
            # agent.json references: "{pkg_name}/{filename}"
            
            assets_to_check = [
                agent.get("modelUrlSlim"),
                agent.get("thumbnail")
            ]
            if agent.get("modelUrlSymbols"):
                assets_to_check.append(agent["modelUrlSymbols"][0].get("symbolName"))
                
            for asset in assets_to_check:
                if asset and asset not in file_list:
                    print(f"  Error: Asset referenced in JSON not found in ZIP: {asset}")

            # If fixed, we need to rewrite the zip
            # ZipFile doesn't support easy update of one file without copying others? 
            # Actually 'w' overwrites, 'a' appends (but doesn't replace).
            # Best way is to read all, then write all to new zip, then replace.
            
            if is_fixed:
                temp_zip_path = zip_path + ".temp"
                with zipfile.ZipFile(zip_path, 'r') as zin:
                    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                        for item in zin.infolist():
                            if item.filename == "agent.json":
                                zout.writestr("agent.json", json.dumps(data, indent=4, ensure_ascii=False))
                            else:
                                zout.writestr(item, zin.read(item.filename))
                
                shutil.move(temp_zip_path, zip_path)
                print("  Updated ZIP file with fixed JSON.")
            
        except Exception as e:
            print(f"  Exception: {e}")

if __name__ == "__main__":
    fix_and_validate()
