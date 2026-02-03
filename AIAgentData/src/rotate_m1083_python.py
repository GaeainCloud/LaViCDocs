import trimesh
import numpy as np
import os

# Define path
model_path = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\downloads\M1083_A1P2_Truck_AI_Rodin.glb"

if not os.path.exists(model_path):
    print(f"Error: File not found at {model_path}")
    exit(1)

print(f"Loading {model_path}...")
# force='scene' ensures we always get a Scene object even if it's a single mesh
scene = trimesh.load(model_path, force='scene')

# Create rotation matrix: 180 degrees around Y axis (which is Up in glTF)
# Rotation around Y axis:
# [ cos(theta)  0  sin(theta)  0]
# [ 0           1  0           0]
# [-sin(theta)  0  cos(theta)  0]
# [ 0           0  0           1]
# For 180 deg (pi radians): cos=-1, sin=0
matrix = np.eye(4)
matrix[0, 0] = -1
matrix[2, 2] = -1

print("Applying 180 degree rotation around Y axis...")
scene.apply_transform(matrix)

print(f"Exporting to {model_path}...")
scene.export(model_path)
print("Done.")