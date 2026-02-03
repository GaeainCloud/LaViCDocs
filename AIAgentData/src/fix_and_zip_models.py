import os
import json
import subprocess
import trimesh
import numpy as np

def rotate_m1083():
    target_file = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\M1083_A1P2_Truck\M1083_A1P2_Truck\M1083_A1P2_Truck_AI_Rodin.glb"
    if os.path.exists(target_file):
        print(f"Rotating {target_file}...")
        try:
            # force='scene' ensures we always get a Scene object
            scene = trimesh.load(target_file, force='scene')
            
            # Create rotation matrix: 180 degrees around Y axis (which is Up in glTF)
            # [ cos(theta)  0  sin(theta)  0]
            # [ 0           1  0           0]
            # [-sin(theta)  0  cos(theta)  0]
            # [ 0           0  0           1]
            # For 180 deg: cos=-1, sin=0
            matrix = np.eye(4)
            matrix[0, 0] = -1
            matrix[2, 2] = -1
            
            scene.apply_transform(matrix)
            scene.export(target_file)
            print("Rotation successful.")
        except Exception as e:
            print(f"Rotation failed: {e}")
    else:
        print(f"Target file for rotation not found: {target_file}")

def fix_agent_json(models_dir):
    try:
        items = os.listdir(models_dir)
    except FileNotFoundError:
        print(f"Error: Directory not found: {models_dir}")
        return

    dirs = [d for d in items if os.path.isdir(os.path.join(models_dir, d)) and d != "assets"]

    print(f"Found directories to process: {dirs}")

    for drone_name in dirs:
        folder_path = os.path.join(models_dir, drone_name)
        json_path = os.path.join(folder_path, "agent.json")
        
        if not os.path.exists(json_path):
            print(f"Warning: {json_path} not found. Skipping.")
            continue
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            updated = False
            
            # Helper function to update a single agent dict
            def update_agent_dict(agent_dict, d_name):
                is_updated = False
                
                # 1. Update 'model' object fields
                if 'model' in agent_dict:
                    agent_dict['model']['modelName'] = d_name
                    # Thumbnail
                    if 'thumbnail' in agent_dict['model']:
                        thumb_filename = f"{d_name}.png"
                        agent_dict['model']['thumbnail']['url'] = f"{d_name}/{thumb_filename}"
                        agent_dict['model']['thumbnail']['ossSig'] = thumb_filename
                    
                    # Map Icon (Military Symbol)
                    if 'mapIconUrl' in agent_dict['model']:
                        mil_filename = f"{d_name}_mil.png"
                        agent_dict['model']['mapIconUrl']['url'] = f"{d_name}/{mil_filename}"
                        agent_dict['model']['mapIconUrl']['ossSig'] = mil_filename

                    # Dim Model Urls (GLB)
                    if 'dimModelUrls' in agent_dict['model'] and isinstance(agent_dict['model']['dimModelUrls'], list):
                         for dim_model in agent_dict['model']['dimModelUrls']:
                             # We assume we update all of them or just the first one?
                             # Let's update all to point to the new rodin model
                             glb_filename = f"{d_name}_AI_Rodin.glb"
                             dim_model['url'] = f"{d_name}/{glb_filename}"
                             dim_model['ossSig'] = glb_filename
                    
                    is_updated = True
                    
                # 2. Update root-level GLB paths
                glb_filename = f"{d_name}_AI_Rodin.glb"
                glb_path = f"{d_name}/{glb_filename}"
                
                if 'modelUrlSlim' in agent_dict:
                    agent_dict['modelUrlSlim'] = glb_path
                    is_updated = True
                if 'modelUrlFat' in agent_dict:
                    agent_dict['modelUrlFat'] = glb_path
                    is_updated = True
                    
                # 3. Update root-level Symbols
                if 'modelUrlSymbols' in agent_dict and isinstance(agent_dict['modelUrlSymbols'], list):
                    for symbol in agent_dict['modelUrlSymbols']:
                        if symbol.get('symbolSeries') == 1:
                            symbol_filename = f"{d_name}.png"
                            symbol_path = f"{d_name}/{symbol_filename}"
                            symbol['symbolName'] = symbol_path
                            symbol['thumbnail'] = symbol_path
                            is_updated = True
                        elif symbol.get('symbolSeries') == 2:
                            mil_filename = f"{d_name}_mil.png"
                            mil_path = f"{d_name}/{mil_filename}"
                            symbol['symbolName'] = mil_path
                            symbol['thumbnail'] = mil_path
                            is_updated = True
                            
                return is_updated

            if isinstance(data, list):
                for item in data:
                    if update_agent_dict(item, drone_name):
                        updated = True
            elif isinstance(data, dict):
                if update_agent_dict(data, drone_name):
                    updated = True
                    
            if updated:
                print(f"Updated fields for {drone_name}")
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                print(f"No updates needed for {json_path}")
                
        except Exception as e:
            print(f"Failed to process {json_path}: {e}")

if __name__ == "__main__":
    # Rotate M1083 model first
    rotate_m1083()

    # base_dir = r"D:\AIProduct\GAEALaViC\AIAgentData\models"
    # Get models dir relative to this script
    # base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models"
    
    print("Starting agent.json fix...")
    fix_agent_json(base_dir)
    
    print("\nStarting re-zipping...")
    # Call the zip script
    zip_script = os.path.join(os.path.dirname(__file__), "zip_models.py")
    subprocess.run(["python", zip_script], cwd=os.path.dirname(base_dir))
