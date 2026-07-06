from logger import get_logger
log = get_logger(__name__)
import bpy
import os
import math

from config import MODELS_DIR

base_dir = str(MODELS_DIR)
models = [
    "大疆Matrice 300RTK无人机",
    "纵横CW-15无人机",
    "亿航EH216-S无人机",
    "沃飞长空AE200",
    "峰飞CarrayAll无人机",
    "Dongfeng-15_Missile_Launcher",
    "M1083_A1P2_Truck",
    "Polaris_MRZR_Alpha",
    "Oshkosh_JLTV",
    "Dongfeng_Mengshi_CSK181",
    "Norinco_Lynx_CS_VP4",
]


def process_model(drone_name):
    glb_path = os.path.join(base_dir, drone_name, drone_name, f"{drone_name}_AI_Rodin.glb")
    if not os.path.exists(glb_path):
        log.info(f"File not found: {glb_path}")
        return

    log.info(f"Processing {glb_path}...")
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)

    bpy.ops.import_scene.gltf(filepath=glb_path)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.transform.rotate(value=math.radians(180), orient_axis="Z", orient_type="GLOBAL")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", use_selection=True)
    log.info(f"Successfully modified and exported {glb_path}")


for model in models:
    process_model(model)
