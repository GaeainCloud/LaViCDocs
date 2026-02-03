import bpy
import os
import math

# Define the models to process
# Using absolute paths to be safe
base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models"
models = [
    "大疆Matrice 300RTK无人机",
    "纵横CW-15无人机",
    "亿航EH216-S无人机",
    "沃飞长空AE200",
    "峰飞CarrayAll无人机"
]

def process_model(drone_name):
    # Construct path: models/{name}/{name}/{name}_AI_Rodin.glb
    glb_path = os.path.join(base_dir, drone_name, drone_name, f"{drone_name}_AI_Rodin.glb")
    
    if not os.path.exists(glb_path):
        print(f"File not found: {glb_path}")
        return

    print(f"Processing {glb_path}...")
    
    # 1. Clear Scene
    # Ensure in Object Mode
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
        
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Purge orphan data to ensure clean slate
    for block in bpy.data.meshes:
        if block.users == 0: bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0: bpy.data.materials.remove(block)
    for block in bpy.data.textures:
        if block.users == 0: bpy.data.textures.remove(block)
    for block in bpy.data.images:
        if block.users == 0: bpy.data.images.remove(block)

    # 2. Import GLB
    try:
        bpy.ops.import_scene.gltf(filepath=glb_path)
    except Exception as e:
        print(f"Error importing {glb_path}: {e}")
        return

    # 3. Rotate
    # Select all objects
    bpy.ops.object.select_all(action='SELECT')
    
    # Check if we have objects
    selected = bpy.context.selected_objects
    if not selected:
        # Fallback if context is weird
        selected = [o for o in bpy.data.objects if o.users > 0]
        for o in selected:
            o.select_set(True)
    
    if not selected:
        print(f"No objects found in {glb_path}")
        return

    # Rotate -90 degrees around X axis (Global)
    # This transforms Z-up (Blender) to Y-up (Target) manually if needed, 
    # OR corrects an orientation that is "lying down".
    # User asked for "Y-axis up".
    bpy.ops.transform.rotate(value=math.radians(-90), orient_axis='X', orient_type='GLOBAL')
    
    # 4. Apply Rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    
    # 5. Export
    # Export with Y-up (default)
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', use_selection=True)
    print(f"Successfully modified and exported {glb_path}")

# Run for all models
for model in models:
    process_model(model)
