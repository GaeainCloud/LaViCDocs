"""Mandatory aircraft orientation policy for LaViC asset generation."""

import numpy as np
import trimesh

BLENDER_AIRCRAFT_EXPORT_YUP = False
THREEJS_AIRCRAFT_IMPORT_UP_AXIS = "Z"
THREEJS_AIRCRAFT_IMPORT_ROTATE_X_DEG = 90
AIRCRAFT_HEADING_NORMALIZATION_AXIS = "Z"
AIRCRAFT_HEADING_NORMALIZATION_DEG = -90
AIRCRAFT_CANONICAL_FORWARD_AXIS = "+X"
AIRCRAFT_CANONICAL_UP_AXIS = "+Z"
AIRCRAFT_CANONICAL_WING_AXIS = "Y"


def assert_blender_aircraft_export_policy(export_yup):
    """Aircraft exported from Blender must not bake Y-up conversion."""
    if export_yup is not BLENDER_AIRCRAFT_EXPORT_YUP:
        raise RuntimeError(
            "Aircraft Blender export policy violation: export_yup must be False. "
            "LaViC import follows the three.js Z-up pipeline and then rotates +90 degrees on X."
        )


def get_aircraft_policy_summary():
    return (
        "Aircraft policy: Blender export uses export_yup=False; "
        "LaViC import follows three.js Z-up and applies X +90°; "
        "if the nose still points to +Y after import, apply heading normalization Z -90°; "
        "final pose must be nose +X, back +Z, wings along Y."
    )


def normalize_aircraft_heading_glb(glb_path, degrees=AIRCRAFT_HEADING_NORMALIZATION_DEG):
    """Normalize aircraft heading so the nose faces +X after client import."""
    if not degrees:
        return

    scene = trimesh.load(glb_path, force="scene")
    rot = trimesh.transformations.rotation_matrix(np.radians(degrees), [0, 0, 1])
    scene.apply_transform(rot)
    with open(glb_path, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))


def prune_aircraft_loose_parts_glb(glb_path, centroid_eps_ratio=0.08, min_component_faces=40):
    """
    Remove obviously detached floating parts from aircraft meshes and keep the
    main spatial cluster around the aircraft body.
    """
    scene = trimesh.load(glb_path, force="scene")
    mesh = scene.to_geometry()
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        return {"kept_faces": 0, "total_faces": 0, "cluster_count": 0}

    nodes = np.arange(len(mesh.faces))
    if len(mesh.face_adjacency) == 0:
        return {"kept_faces": len(mesh.faces), "total_faces": len(mesh.faces), "cluster_count": 1}

    components = trimesh.graph.connected_components(
        mesh.face_adjacency, nodes=nodes, min_len=1, engine="scipy"
    )
    if len(components) <= 1:
        return {"kept_faces": len(mesh.faces), "total_faces": len(mesh.faces), "cluster_count": 1}

    infos = []
    for comp in components:
        sub = mesh.submesh([comp], append=True, repair=False)
        infos.append(
            {
                "faces": int(len(comp)),
                "face_idx": np.asarray(comp, dtype=np.int64),
                "centroid": sub.bounding_box.centroid,
                "bounds": sub.bounds,
            }
        )

    filtered = [i for i in infos if i["faces"] >= min_component_faces]
    if not filtered:
        filtered = infos

    xy_span = mesh.bounds[1][:2] - mesh.bounds[0][:2]
    eps = max(float(np.max(xy_span)) * centroid_eps_ratio, 0.12)

    parents = list(range(len(filtered)))

    def find(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x

    def union(a, b):
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parents[rb] = ra

    for i in range(len(filtered)):
        for j in range(i + 1, len(filtered)):
            a = filtered[i]["centroid"][:2]
            b = filtered[j]["centroid"][:2]
            if np.linalg.norm(a - b) <= eps:
                union(i, j)

    clusters = {}
    for i, info in enumerate(filtered):
        clusters.setdefault(find(i), []).append(info)

    scored = []
    for group in clusters.values():
        face_sum = sum(i["faces"] for i in group)
        centroid = np.mean([i["centroid"] for i in group], axis=0)
        score = face_sum / (1.0 + np.linalg.norm(centroid[:2]))
        scored.append((score, face_sum, centroid, group))

    scored.sort(key=lambda x: x[0], reverse=True)
    _, kept_faces, _, best_group = scored[0]

    keep_faces = np.concatenate([g["face_idx"] for g in best_group])
    cleaned = mesh.submesh([keep_faces], append=True, repair=False)

    with open(glb_path, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(trimesh.Scene(cleaned)))

    return {
        "kept_faces": int(kept_faces),
        "total_faces": int(len(mesh.faces)),
        "cluster_count": int(len(clusters)),
    }


def inspect_aircraft_mesh_quality(glb_path):
    """Return coarse geometric quality metrics for deciding whether to keep a generated aircraft."""
    scene = trimesh.load(glb_path, force="scene")
    mesh = scene.to_geometry()
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        return {"faces": 0, "length": 0.0, "span": 0.0, "height": 0.0, "span_ratio": 0.0, "height_ratio": 0.0}

    extents = np.asarray(mesh.extents, dtype=float)
    length = float(max(extents[0], extents[1]))
    span = float(min(extents[0], extents[1]))
    height = float(extents[2])
    span_ratio = span / length if length > 1e-6 else 0.0
    height_ratio = height / length if length > 1e-6 else 0.0
    return {
        "faces": int(len(mesh.faces)),
        "length": length,
        "span": span,
        "height": height,
        "span_ratio": span_ratio,
        "height_ratio": height_ratio,
    }
