
import json
import os
import zipfile

# Configuration
base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples\想定_防空反导-v1.60.9-null-2026年02月10日07时01分46秒"
json_path = os.path.join(base_dir, "simulation.json")
output_zip_path = os.path.join(os.path.dirname(base_dir), "想定_防空反导-v1.60.9-修复版.zip")

def fix_simulation():
    print(f"Reading {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle list root structure
    if isinstance(data, list) and len(data) > 0:
        agent_instances = data[0].get("agentInstances", [])
    elif isinstance(data, dict):
        agent_instances = data.get("agentInstances", [])
    else:
        print("Error: Unknown JSON structure")
        return False
    
    # Track modifications
    modified_counts = {"Conflict Dolphin": 0, "Majestic Penguin": 0}

    for agent in agent_instances:
        name = agent.get("instanceName")
        
        if name == "Conflict Dolphin":
            print(f"Fixing {name}...")
            # Structure: waypoints -> [0] -> wps -> list of points -> wpsCore -> [4] is time
            if "waypoints" in agent and len(agent["waypoints"]) > 0:
                wps_list = agent["waypoints"][0].get("wps", [])
                # Update times: 0, 110, 170
                new_times = [0.0, 110.0, 170.0]
                
                for i, point in enumerate(wps_list):
                    if i < len(new_times):
                        old_time = point["wpsCore"][4]
                        point["wpsCore"][4] = new_times[i]
                        print(f"  Point {i}: Time changed from {old_time} to {new_times[i]}")
                        modified_counts[name] += 1
                        
        elif name == "Majestic Penguin":
            print(f"Fixing {name}...")
            if "waypoints" in agent and len(agent["waypoints"]) > 0:
                wps_list = agent["waypoints"][0].get("wps", [])
                # Update times: 0, 380, 620
                new_times = [0.0, 380.0, 620.0]
                
                for i, point in enumerate(wps_list):
                    if i < len(new_times):
                        old_time = point["wpsCore"][4]
                        point["wpsCore"][4] = new_times[i]
                        print(f"  Point {i}: Time changed from {old_time} to {new_times[i]}")
                        modified_counts[name] += 1

    # Save back to JSON
    print(f"Saving updated JSON to {json_path}...")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print("JSON update complete.")
    return True

def pack_zip():
    print(f"Creating ZIP archive at {output_zip_path}...")
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through the directory and add files
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate relative path for the zip entry
                arcname = os.path.relpath(file_path, base_dir)
                print(f"  Adding {arcname}")
                zipf.write(file_path, arcname)
    print("ZIP creation complete.")

if __name__ == "__main__":
    if fix_simulation():
        pack_zip()
