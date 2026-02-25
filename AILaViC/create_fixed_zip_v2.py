
import json
import os
import zipfile
import shutil

# Configuration
# Source is the currently unzipped folder (which already has the modified JSON from previous step)
source_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples\想定_防空反导-v1.60.9-null-2026年02月10日07时01分46秒"
# Parent directory
parent_dir = os.path.dirname(source_dir)
# Target fixed directory name
fixed_dir_name = "想定_防空反导-v1.60.9-修复版"
fixed_dir_path = os.path.join(parent_dir, fixed_dir_name)
# Output zip path
output_zip_path = os.path.join(parent_dir, f"{fixed_dir_name}.zip")

def create_fixed_version_folder():
    print(f"Creating fixed version folder at: {fixed_dir_path}")
    
    # Clean up target if exists
    if os.path.exists(fixed_dir_path):
        print(f"Removing existing target directory: {fixed_dir_path}")
        shutil.rmtree(fixed_dir_path)
    
    # Copy source to target
    print(f"Copying from {source_dir} to {fixed_dir_path}...")
    shutil.copytree(source_dir, fixed_dir_path)
    print("Folder copy complete.")
    
    return True

def verify_and_fix_json():
    # Verify the JSON in the NEW folder just to be sure
    json_path = os.path.join(fixed_dir_path, "simulation.json")
    print(f"Verifying/Fixing JSON at {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle list root structure if necessary (though we know it's list from previous step)
    if isinstance(data, list) and len(data) > 0:
        agent_instances = data[0].get("agentInstances", [])
    elif isinstance(data, dict):
        agent_instances = data.get("agentInstances", [])
    else:
        print("Error: Unknown JSON structure")
        return False
    
    modified_counts = {"Conflict Dolphin": 0, "Majestic Penguin": 0}
    
    # Expected times based on previous calculation
    expected_times = {
        "Conflict Dolphin": [0.0, 110.0, 170.0],
        "Majestic Penguin": [0.0, 380.0, 620.0]
    }

    needs_save = False

    for agent in agent_instances:
        name = agent.get("instanceName")
        if name in expected_times:
            if "waypoints" in agent and len(agent["waypoints"]) > 0:
                wps_list = agent["waypoints"][0].get("wps", [])
                targets = expected_times[name]
                
                for i, point in enumerate(wps_list):
                    if i < len(targets):
                        current_time = point["wpsCore"][4]
                        target_time = targets[i]
                        
                        # Use a small epsilon for float comparison or just direct replacement
                        if abs(current_time - target_time) > 0.001:
                            print(f"  Fixing {name} Point {i}: {current_time} -> {target_time}")
                            point["wpsCore"][4] = target_time
                            modified_counts[name] += 1
                            needs_save = True
                        else:
                            # Already correct
                            pass

    if needs_save:
        print(f"Saving verified JSON to {json_path}...")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("JSON fixed and saved.")
    else:
        print("JSON verification passed (already fixed).")
        
    return True

def pack_zip():
    print(f"Creating ZIP archive at {output_zip_path}...")
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through the fixed directory and add files
        # Important: The user wants "Generate Zip", usually meaning the zip contains the folder.
        # But previous structure was flat contents.
        # "先形成一个修复版本的文件夹，然后再生成zip" -> 
        # Usually means unzip -> folder -> zip -> zip contains folder.
        # Let's check how standard zips are. Usually they contain the root folder.
        # The previous unzip resulted in "想定_防空反导-v1.60.9-null-2026年02月10日07时01分46秒" folder because I unzipped TO current dir or it had a root?
        # Let's assume the user wants the ZIP to contain the folder "想定_防空反导-v1.60.9-修复版".
        
        root_len = len(os.path.dirname(fixed_dir_path))
        
        for root, dirs, files in os.walk(fixed_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                # arcname should include the folder name "想定_防空反导-v1.60.9-修复版"
                arcname = file_path[root_len:].lstrip(os.sep)
                print(f"  Adding {arcname}")
                zipf.write(file_path, arcname)
                
    print("ZIP creation complete.")

if __name__ == "__main__":
    if create_fixed_version_folder():
        if verify_and_fix_json():
            pack_zip()
