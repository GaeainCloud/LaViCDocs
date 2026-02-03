import os
import trimesh
import numpy as np
import zipfile
import json
import shutil

# 目标车辆列表
VEHICLES = [
    "M1083_A1P2_Truck",
    "Dongfeng_Mengshi_CSK181",
    "Norinco_Lynx_CS_VP4",
    "Oshkosh_JLTV",
    "Polaris_MRZR_Alpha",
    # "Dongfeng-15_Missile_Launcher" # 可选，如果用户是指那5个英文名的
]

BASE_DIR = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models"

def process_and_package(model_name):
    print(f"Processing {model_name}...")
    
    model_root = os.path.join(BASE_DIR, model_name)
    inner_dir = os.path.join(model_root, model_name)
    glb_path = os.path.join(inner_dir, f"{model_name}_AI_Rodin.glb")
    
    if not os.path.exists(glb_path) or True: # Force restore to ensure clean state for rotation
        # print(f"  GLB not found at {glb_path}, checking downloads...")
        # 尝试从 downloads 恢复（如果存在）
        download_path = os.path.join(BASE_DIR, "downloads", f"{model_name}_AI_Rodin.glb")
        if os.path.exists(download_path):
            shutil.copy2(download_path, glb_path)
            print(f"  Restored raw model from {download_path}")
        else:
            print(f"  Error: Model file not found for {model_name}")
            return

    # 1. 旋转模型 
    try:
        print(f"  Loading GLB...")
        scene = trimesh.load(glb_path, force='scene')
        
        # A. 绕 Z 轴旋转 180 度 (修正朝向)
        matrix_z = trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1])
        scene.apply_transform(matrix_z)
        print(f"  Applied Z-axis 180 rotation.")

        # B. 绕 X 轴旋转 -90 度 (Z-up -> Y-up)
        matrix_x = trimesh.transformations.rotation_matrix(-np.pi/2, [1, 0, 0])
        scene.apply_transform(matrix_x)
        print(f"  Applied X-axis -90 rotation (Y-up conversion).")
        
        # 导出
        print(f"  Exporting rotated GLB...")
        # export 返回的是 bytes
        glb_data = scene.export(file_type='glb')
        with open(glb_path, 'wb') as f:
            f.write(glb_data)
        print(f"  Rotated model saved.")
        
    except Exception as e:
        print(f"  Error processing GLB: {e}")
        return

    # 2. 打包 (Flat Structure: agent.json + Folder)
    zip_path = os.path.join(BASE_DIR, f"{model_name}.zip")
    agent_json_path = os.path.join(model_root, "agent.json")
    
    if not os.path.exists(agent_json_path):
        print(f"  Error: agent.json not found at {agent_json_path}")
        return

    print(f"  Creating ZIP at {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 添加 agent.json 到根目录
            zf.write(agent_json_path, "agent.json")
            
            # 添加资源文件夹
            for filename in os.listdir(inner_dir):
                file_path = os.path.join(inner_dir, filename)
                if os.path.isfile(file_path):
                    # 在ZIP中的路径: {ModelName}/{Filename}
                    arcname = f"{model_name}/{filename}"
                    zf.write(file_path, arcname)
        print(f"  Packaging complete.")
        
    except Exception as e:
        print(f"  Error packaging ZIP: {e}")

if __name__ == "__main__":
    for vehicle in VEHICLES:
        process_and_package(vehicle)
    print("All tasks finished.")
