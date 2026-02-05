import json
import zipfile
import os

MODELS_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models"
PACKAGES = [
    "J-20_Mighty_Dragon",
    "F-22_Raptor",
    "F-35_Lightning_II",
    "Su-57_Felon"
]

PATH_FIELDS = [
    "modelUrlSlim",
    "modelUrlFat",
    "modelUrlMedium",
    "modelUrlPAK",
    "thumbnail"
]

def deep_check():
    for pkg_name in PACKAGES:
        zip_path = os.path.join(MODELS_DIR, f"{pkg_name}.zip")
        print(f"\n==================================================")
        print(f"Checking {pkg_name}.zip")
        print(f"==================================================")
        
        if not os.path.exists(zip_path):
            print(f"ERROR: File not found: {zip_path}")
            continue

        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # 1. Get Zip Content
                file_list = z.namelist()
                print(f"Zip Contents: {file_list}")
                
                # 2. Read JSON
                if "agent.json" not in file_list:
                    print("ERROR: agent.json missing!")
                    continue
                    
                json_content = z.read("agent.json").decode('utf-8')
                data = json.loads(json_content)
                
                if isinstance(data, list):
                    agent = data[0]
                else:
                    agent = data
                    print("WARNING: Root is not a list (should be fixed already)")

                # 3. Check Fields
                all_good = True
                
                # Check simple path fields
                for field in PATH_FIELDS:
                    val = agent.get(field)
                    print(f"  Field '{field}': '{val}'")
                    
                    if val:
                        # Normalize path separators for comparison if needed, but zip usually uses /
                        if val not in file_list:
                             print(f"    -> ERROR: File referenced in {field} NOT found in zip!")
                             all_good = False
                        else:
                             print(f"    -> OK: Found in zip.")
                    else:
                        print(f"    -> (Empty, skipping)")

                # Check symbols
                symbols = agent.get("modelUrlSymbols", [])
                if symbols:
                    print(f"  Field 'modelUrlSymbols': {len(symbols)} items")
                    for idx, sym in enumerate(symbols):
                        s_name = sym.get("symbolName")
                        s_thumb = sym.get("thumbnail")
                        print(f"    Item {idx}: symbolName='{s_name}', thumbnail='{s_thumb}'")
                        
                        if s_name:
                            if s_name not in file_list:
                                print(f"      -> ERROR: symbolName file NOT found in zip!")
                                all_good = False
                            else:
                                print(f"      -> OK: symbolName found.")
                        
                        if s_thumb:
                            if s_thumb not in file_list:
                                print(f"      -> ERROR: thumbnail file NOT found in zip!")
                                all_good = False
                            else:
                                print(f"      -> OK: thumbnail found.")
                else:
                    print("  Field 'modelUrlSymbols': [] (Empty)")

                if all_good:
                    print(f"\nRESULT: {pkg_name} PASSED validation.")
                else:
                    print(f"\nRESULT: {pkg_name} FAILED validation.")

        except Exception as e:
            print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    deep_check()
