"""Shared ship orientation policy for LaViC asset generation."""

import numpy as np
import trimesh

SHIP_CANONICAL_FORWARD_AXIS = "+X"
SHIP_CANONICAL_UP_AXIS = "+Z"
SHIP_CANONICAL_BEAM_AXIS = "Y"
SHIP_LEVELING_AXIS = "Y"
SHIP_LEVELING_DEG = -90
SHIP_ROLL_FIX_AXIS = "X"
SHIP_ROLL_FIX_DEG = 90
SHIP_HEADING_NORMALIZATION_AXIS = "Z"
SHIP_HEADING_NORMALIZATION_DEG = -90
SHIP_POST_ROLL_X_OVERRIDES = {
    "Liaoning_Aircraft_Carrier": 90,
    "Shandong_Aircraft_Carrier": 90,
    "HMS_Queen_Elizabeth_R08": 90,
    "Charles_de_Gaulle_R91": 90,
    "USS_America_LHA6": 90,
    "JS_Izumo_DDH183": 90,
}


def get_ship_policy_summary():
    return (
        "Ship policy: first keep the deck level with +Z up; "
        "if a generated ship stands upright with its longest axis on +Z, apply leveling Y -90°; "
        "if a generated ship is side-rolled and its Z height is still larger than its Y beam, apply roll fix X +90°; "
        "if the bow still points to +Y after import, apply heading normalization Z -90°; "
        "for validated carrier hulls that still side-roll in LaViC, apply a model-specific X +90° post-roll override; "
        "final pose must be bow +X, deck +Z, beam along Y."
    )


def apply_manual_x_rotation_glb(glb_path, degrees):
    if not degrees:
        return False

    scene = trimesh.load(glb_path, force="scene")
    rot = trimesh.transformations.rotation_matrix(np.radians(degrees), [1, 0, 0])
    scene.apply_transform(rot)
    mesh = scene.to_geometry()
    bounds = mesh.bounds
    center_x = float((bounds[0][0] + bounds[1][0]) / 2.0)
    center_y = float((bounds[0][1] + bounds[1][1]) / 2.0)
    min_z = float(bounds[0][2])
    trans = trimesh.transformations.translation_matrix([-center_x, -center_y, -min_z])
    scene.apply_transform(trans)
    with open(glb_path, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))
    return True


def inspect_ship_client_roll(glb_path):
    """
    Predict whether a ship will still look side-rolled in LaViC after import.

    Empirically, for these deck ships the client-side display behaves like the
    raw GLB Y/Z dimensions are swapped. If raw Y remains larger than raw Z,
    the deck still appears vertical in LaViC and needs one more X +90° fix.
    """
    scene = trimesh.load(glb_path, force="scene")
    mesh = scene.to_geometry()
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        return {"extents": [0.0, 0.0, 0.0], "will_side_roll": False}
    extents = np.asarray(mesh.extents, dtype=float)
    return {
        "extents": [float(x) for x in extents],
        "will_side_roll": bool(extents[1] > extents[2]),
    }


def apply_known_ship_roll_override(glb_path, model_name):
    inspection = inspect_ship_client_roll(glb_path)
    if not inspection["will_side_roll"]:
        return False, 0
    degrees = SHIP_POST_ROLL_X_OVERRIDES.get(model_name, SHIP_ROLL_FIX_DEG)
    applied = apply_manual_x_rotation_glb(glb_path, degrees)
    return applied, degrees


def normalize_ship_heading_glb(glb_path, degrees=SHIP_HEADING_NORMALIZATION_DEG):
    """Normalize ship heading so the bow faces +X after client import."""
    if not degrees:
        return

    scene = trimesh.load(glb_path, force="scene")
    rot = trimesh.transformations.rotation_matrix(np.radians(degrees), [0, 0, 1])
    scene.apply_transform(rot)
    with open(glb_path, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))


def normalize_ship_pose_glb(glb_path):
    """
    Normalize ship pose for LaViC:
    1) If the longest dimension is vertical, lay the hull flat with Y -90°.
    2) If the hull is side-rolled (height > beam), rotate X +90°.
    3) If the longest horizontal dimension still aligns to Y, rotate Z -90°.
    4) Re-ground the mesh so min Z = 0.
    """
    scene = trimesh.load(glb_path, force="scene")
    mesh = scene.to_geometry()
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        return {"leveled": False, "heading_fixed": False, "extents": [0.0, 0.0, 0.0]}

    leveled = False
    heading_fixed = False

    extents = np.asarray(mesh.extents, dtype=float)
    if extents[2] > max(extents[0], extents[1]):
        rot = trimesh.transformations.rotation_matrix(np.radians(SHIP_LEVELING_DEG), [0, 1, 0])
        scene.apply_transform(rot)
        leveled = True
        mesh = scene.to_geometry()
        extents = np.asarray(mesh.extents, dtype=float)

    rolled = False
    if extents[0] >= max(extents[1], extents[2]) and extents[2] > extents[1]:
        rot = trimesh.transformations.rotation_matrix(np.radians(SHIP_ROLL_FIX_DEG), [1, 0, 0])
        scene.apply_transform(rot)
        rolled = True
        mesh = scene.to_geometry()
        extents = np.asarray(mesh.extents, dtype=float)

    if extents[1] > extents[0]:
        rot = trimesh.transformations.rotation_matrix(np.radians(SHIP_HEADING_NORMALIZATION_DEG), [0, 0, 1])
        scene.apply_transform(rot)
        heading_fixed = True
        mesh = scene.to_geometry()
        extents = np.asarray(mesh.extents, dtype=float)

    bounds = mesh.bounds
    min_z = float(bounds[0][2])
    if abs(min_z) > 1e-6:
        trans = trimesh.transformations.translation_matrix([0.0, 0.0, -min_z])
        scene.apply_transform(trans)
        mesh = scene.to_geometry()
        extents = np.asarray(mesh.extents, dtype=float)

    with open(glb_path, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))

    return {
        "leveled": leveled,
        "rolled": rolled,
        "heading_fixed": heading_fixed,
        "extents": [float(x) for x in extents],
    }
