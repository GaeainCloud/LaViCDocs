import copy
import json
import os
import re
import socket
import time
import uuid
import zipfile
from io import BytesIO

import military_symbol
import numpy as np
import requests
import resvg_py
import trimesh
from PIL import Image
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from trimesh.geometry import align_vectors

from runtime_config import apply_proxy_env, get_models_dir
from validate_all import validate_files

MODEL_NAME = "NSM_Anti_Ship_Missile"
MODEL_NAME_I18N = "NSM反舰导弹"
IMAGE_QUERY = "Naval Strike Missile NSM side view render"
TEMPLATE_JSON = "08boundingMineAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "NSM反舰导弹模型，采用目标跟踪导引动力学用于对海精确打击仿真。"
ENABLE_QUALITY_GATE = False
PREFERRED_IMAGE_URLS = [
    "https://www.renderhub.com/akela-freedom/naval-strike-missile-1/naval-strike-missile-1-01.jpg",
    "https://www.renderhub.com/akela-freedom/naval-strike-missile-1/naval-strike-missile-1-02.jpg",
    "https://www.renderhub.com/akela-freedom/naval-strike-missile-1/naval-strike-missile-1-03.jpg",
]


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


class BlenderMCPClient:
    def __init__(self, host="127.0.0.1", port=9876, timeout_sec=600):
        self.host = host
        self.port = port
        self.timeout_sec = timeout_sec

    def call(self, cmd_type, params=None):
        sock = socket.socket()
        sock.settimeout(self.timeout_sec)
        sock.connect((self.host, self.port))
        try:
            payload = json.dumps({"type": cmd_type, "params": params or {}}).encode("utf-8")
            sock.sendall(payload)
            chunks = []
            while True:
                try:
                    chunk = sock.recv(65536)
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                if len(chunk) < 65536:
                    break
            data = b"".join(chunks).decode("utf-8", "replace")
            return json.loads(data)
        finally:
            sock.close()


def parse_json_between_markers(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"Failed to parse response markers: {text[:500]}")
    raw = text[start + len(start_marker):end].strip()
    return json.loads(raw)


def extract_rodin_submit_info(submit_json):
    task_uuid = submit_json.get("uuid")
    jobs = submit_json.get("jobs") or {}
    subscription_key = jobs.get("subscription_key")
    if task_uuid and subscription_key:
        return task_uuid, subscription_key

    nested = submit_json.get("result") or {}
    if isinstance(nested, dict):
        task_uuid = task_uuid or nested.get("uuid")
        jobs = nested.get("jobs") or jobs
        subscription_key = subscription_key or jobs.get("subscription_key")

    if task_uuid and subscription_key:
        return task_uuid, subscription_key

    raise RuntimeError(
        "Rodin submit response missing uuid/subscription_key. "
        f"top-level keys={sorted(submit_json.keys())}, "
        f"jobs keys={sorted(jobs.keys()) if isinstance(jobs, dict) else jobs}, "
        f"raw={json.dumps(submit_json, ensure_ascii=False)[:1200]}"
    )


def normalize_thumbnail(img):
    canvas = Image.new("RGB", (1400, 900), "white")
    img.thumbnail((1280, 760))
    canvas.paste(img, ((canvas.width - img.width) // 2, (canvas.height - img.height) // 2))
    return canvas


def fetch_real_thumbnail(output_png):
    headers = {"User-Agent": "Mozilla/5.0"}
    best = None
    good_kw = ("nsm", "naval", "strike", "missile", "anti-ship", "antiship")
    bad_kw = (
        "logo",
        "patch",
        "wallpaper",
        "diagram",
        "blueprint",
        "wire",
        "wireframe",
        "texture",
        "material",
        "uv",
        "albedo",
        "normal",
        "roughness",
        "metallic",
        "sheet",
        "atlas",
        "launcher",
        "fighter",
        "cockpit",
        "poster",
        "israelnoticias",
        "armyrecognition",
        "makerworld",
        "cults3d",
        "dreamstime",
        "satellite",
        "janes",
        "analysis",
        "shipyard",
    )

    def consider(url, strict_size=True):
        nonlocal best
        lower = url.lower()
        if any(k in lower for k in bad_kw):
            return
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code != 200:
                return
            if strict_size and len(r.content) < 16000:
                return
            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if strict_size and max(w, h) < 700:
                return
            if (not strict_size) and max(w, h) < 500:
                return
            ratio = w / max(h, 1)
            score = (w * h) + (220000 if 2.5 <= ratio <= 6.5 else 0) + (240000 if any(k in lower for k in good_kw) else 0)
            if "naval-strike-missile-1-01.jpg" in lower:
                score += 1000000
            elif "naval-strike-missile-1-02.jpg" in lower:
                score += 850000
            elif "naval-strike-missile-1-03.jpg" in lower:
                score += 700000
            if best is None or score > best[0]:
                best = (score, normalize_thumbnail(img), url, w, h)
        except Exception:
            return

    for url in PREFERRED_IMAGE_URLS:
        consider(url, strict_size=False)

    if best is None:
        resp = requests.get(
            "https://www.bing.com/images/search",
            params={"q": IMAGE_QUERY, "qft": "filterui:imagesize-large"},
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        html = resp.text
        murls = re.findall(r'"murl":"(.*?)"', html) or re.findall(r"murl&quot;:&quot;(.*?)&quot;", html)
        candidates = []
        for raw in murls:
            url = raw.encode("utf-8").decode("unicode_escape").replace("\\/", "/")
            if url not in candidates:
                candidates.append(url)
        for url in candidates[:80]:
            consider(url)

    if best is None:
        raise RuntimeError("Failed to download a valid NSM thumbnail image.")

    _, image, source_url, w, h = best
    image.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {source_url}")


def generate_military_symbol(output_png):
    svg = military_symbol.get_symbol_svg_string_from_name(
        "Hostile Missile", style="light", bounding_padding=4, use_variants=True
    )
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Hostile Guided Missile", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Hostile Anti-Ship Missile", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        raise RuntimeError("Failed to generate military symbol for NSM missile.")

    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png}")


def build_missile_mesh():
    body_color = [72, 102, 64, 255]
    fin_color = [66, 90, 58, 255]
    dark = [48, 68, 44, 255]
    parts = []

    body = trimesh.creation.cylinder(radius=0.15, height=4.1, sections=48)
    body.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    body.apply_translation([0.0, 0.0, 0.15])
    body.visual.face_colors = body_color
    parts.append(body)

    nose = trimesh.creation.cone(radius=0.15, height=0.55, sections=48)
    nose.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    nose.apply_translation([2.28, 0.0, 0.15])
    nose.visual.face_colors = body_color
    parts.append(nose)

    tail = trimesh.creation.cylinder(radius=0.14, height=0.22, sections=32)
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    tail.apply_translation([-2.05, 0.0, 0.15])
    tail.visual.face_colors = dark
    parts.append(tail)

    front_fin_a = trimesh.creation.box(extents=[0.24, 0.82, 0.04])
    front_fin_a.apply_translation([-0.05, 0.0, 0.18])
    front_fin_a.visual.face_colors = fin_color
    parts.append(front_fin_a)

    front_fin_b = trimesh.creation.box(extents=[0.24, 0.04, 0.82])
    front_fin_b.apply_translation([-0.05, 0.0, 0.18])
    front_fin_b.visual.face_colors = fin_color
    parts.append(front_fin_b)

    rear_fin_a = trimesh.creation.box(extents=[0.26, 0.92, 0.04])
    rear_fin_a.apply_translation([-1.55, 0.0, 0.18])
    rear_fin_a.visual.face_colors = fin_color
    parts.append(rear_fin_a)

    rear_fin_b = trimesh.creation.box(extents=[0.26, 0.04, 0.92])
    rear_fin_b.apply_translation([-1.55, 0.0, 0.18])
    rear_fin_b.visual.face_colors = fin_color
    parts.append(rear_fin_b)

    return trimesh.util.concatenate(parts)


def normalize_missile_pose_glb(glb_path):
    scene = trimesh.load(glb_path, force="scene")
    mesh = scene.to_geometry()
    forward = mesh.principal_inertia_vectors[0]
    scene.apply_transform(align_vectors(forward, [1, 0, 0]))

    # If the missile is still "standing up", roll it flat around the forward axis.
    extents = (scene.bounds[1] - scene.bounds[0]).tolist()
    if extents[2] > extents[1] * 1.5:
        rolled = scene.copy()
        rolled.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [1, 0, 0]))
        rolled_extents = (rolled.bounds[1] - rolled.bounds[0]).tolist()
        if rolled_extents[2] < extents[2]:
            scene = rolled

    bounds = scene.bounds
    min_corner, max_corner = bounds
    scene.apply_translation(
        [
            -((min_corner[0] + max_corner[0]) / 2.0),
            -((min_corner[1] + max_corner[1]) / 2.0),
            -min_corner[2],
        ]
    )
    with open(glb_path, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))
    extents = scene.bounds[1] - scene.bounds[0]
    print(f"[glb] normalized missile pose extents={extents.tolist()} -> {glb_path}")


def missile_quality_needs_fallback(glb_path):
    scene = trimesh.load(glb_path, force="scene")
    mesh = scene.to_geometry()
    extents = mesh.extents

    # A missile should stay slender after normalization: X >> Y,Z.
    if extents[2] > max(extents[1] * 2.0, extents[0] * 0.45):
        print(f"[glb] reject rodin missile: abnormal height extents={extents.tolist()}")
        return True

    fa = mesh.face_adjacency
    if len(fa) == 0:
        return True
    rows = np.concatenate([fa[:, 0], fa[:, 1]])
    cols = np.concatenate([fa[:, 1], fa[:, 0]])
    data = np.ones(len(rows), dtype=np.uint8)
    graph = coo_matrix((data, (rows, cols)), shape=(len(mesh.faces), len(mesh.faces))).tocsr()
    comp_n, labels = connected_components(graph, directed=False)
    counts = np.bincount(labels)
    if comp_n > 500:
        print(f"[glb] reject rodin missile: fragmented components={comp_n}")
        return True

    big = 0
    for idx in np.argsort(counts)[::-1][:12]:
        faces = np.where(labels == idx)[0]
        if len(faces) < 300:
            continue
        sub = mesh.submesh([faces], append=True, repair=False)
        sx, sy, sz = sub.extents
        # Tall pole-like parts are not acceptable for missiles.
        if sz > max(sy * 2.5, sx * 1.2):
            big += 1
    if big:
        print(f"[glb] reject rodin missile: found {big} large vertical detached components")
        return True
    return False


def export_fallback_glb(output_glb):
    mesh = build_missile_mesh()
    scene = trimesh.Scene(mesh)
    with open(output_glb, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))
    print(f"[glb] fallback saved {output_glb}")


def generate_glb_with_blendermcp(image_path, output_glb):
    client = BlenderMCPClient()
    scene_info = client.call("get_scene_info")
    if scene_info.get("status") != "success":
        raise RuntimeError(f"BlenderMCP scene check failed: {scene_info}")

    hyper = client.call("get_hyper3d_status")
    if hyper.get("status") != "success" or not hyper.get("result", {}).get("enabled"):
        raise RuntimeError(f"Hyper3D not ready: {hyper}")

    submit_code = f"""
import bpy, json
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for obj in list(bpy.data.objects):
    if obj.users == 0:
        bpy.data.objects.remove(obj)
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
server = getattr(bpy.types, 'blendermcp_server', None)
with open(r'{image_path}', 'rb') as f:
    img_bytes = f.read()
resp = server.create_rodin_job(
    text_prompt='Naval Strike Missile NSM anti-ship missile, complete connected missile body, stealthy sea-skimming anti-ship missile, clean single missile, pointed nose, cropped delta wings, rear tail fins, no launcher, no detached parts, no floating geometry, clean topology, clean side profile',
    images=[('.png', img_bytes)]
)
print('RESP_JSON_START')
print(json.dumps(resp))
print('RESP_JSON_END')
"""
    last_error = None
    for attempt in range(3):
        submit = client.call("execute_code", {"code": submit_code})
        result_text = (submit.get("result") or {}).get("result", "")
        submit_json = parse_json_between_markers(result_text, "RESP_JSON_START", "RESP_JSON_END")
        try:
            task_uuid, subscription_key = extract_rodin_submit_info(submit_json)
            break
        except Exception as exc:
            last_error = exc
            print(f"[rodin] submit parse failed on attempt {attempt + 1}: {exc}")
            time.sleep(2)
    else:
        raise RuntimeError(str(last_error))

    for _ in range(60):
        status = client.call("poll_rodin_job_status", {"subscription_key": subscription_key})
        statuses = status.get("result", {}).get("status_list", [])
        print(f"[rodin] status {statuses}")
        if statuses and all(str(x).lower() == "done" for x in statuses):
            break
        if statuses and any(str(x).lower() == "failed" for x in statuses):
            raise RuntimeError(f"Rodin job failed: {status}")
        time.sleep(10)
    else:
        raise RuntimeError("Rodin job timed out for NSM missile.")

    imported = client.call("import_generated_asset", {"task_uuid": task_uuid, "name": MODEL_NAME})
    if imported.get("status") != "success" or not imported.get("result", {}).get("succeed"):
        raise RuntimeError(f"Rodin import failed: {imported}")

    export_code = f"""
import bpy, os
import mathutils
name = '{MODEL_NAME}'
out = r'{output_glb}'
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not meshes:
    raise RuntimeError('No mesh objects found after Rodin import')
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
obj.name = name
if getattr(obj.data, 'name', None) is not None:
    obj.data.name = name
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bbox = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
min_x = min(v.x for v in bbox); max_x = max(v.x for v in bbox)
min_y = min(v.y for v in bbox); max_y = max(v.y for v in bbox)
min_z = min(v.z for v in bbox)
obj.location.x -= (min_x + max_x) / 2.0
obj.location.y -= (min_y + max_y) / 2.0
obj.location.z -= min_z
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
for o in list(bpy.context.scene.objects):
    if o != obj and o.type in ('CAMERA', 'LIGHT', 'MESH', 'EMPTY', 'CURVE', 'ARMATURE'):
        bpy.data.objects.remove(o, do_unlink=True)
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True)
print('EXPORTED', out)
"""
    exported = client.call("execute_code", {"code": export_code})
    if exported.get("status") != "success":
        raise RuntimeError(f"Blender export failed: {exported}")
    print(f"[glb] rodin saved {output_glb}")


def generate_agent_json(output_json):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_path = os.path.join(base_dir, "examples", TEMPLATE_JSON)
    with open(template_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    agent = copy.deepcopy(data[0] if isinstance(data, list) else data)
    agent["agentKey"] = f"AGENTKEY_{uuid.uuid4().int}"
    agent["agentName"] = MODEL_NAME
    agent["agentNameI18n"] = MODEL_NAME_I18N
    agent["agentDesc"] = AGENT_DESC
    agent["agentCoreFunc"] = AGENT_DESC
    agent["agentKeyword"] = "nsm_anti_ship_missile"

    rel_png = f"{MODEL_NAME}/{PNG_FILENAME}"
    rel_mil = f"{MODEL_NAME}/{MIL_FILENAME}"
    rel_glb = f"{MODEL_NAME}/{GLB_FILENAME}"

    agent["modelUrlSlim"] = rel_glb
    agent["modelUrlFat"] = rel_glb
    agent["modelUrlSymbols"] = [
        {"symbolSeries": 1, "symbolName": rel_png, "thumbnail": rel_png},
        {"symbolSeries": 2, "symbolName": rel_mil, "thumbnail": rel_mil},
    ]

    if "model" in agent:
        agent["model"]["modelName"] = MODEL_NAME
        if "thumbnail" in agent["model"]:
            agent["model"]["thumbnail"]["url"] = rel_png
            agent["model"]["thumbnail"]["ossSig"] = PNG_FILENAME
        if "mapIconUrl" in agent["model"]:
            agent["model"]["mapIconUrl"]["url"] = rel_mil
            agent["model"]["mapIconUrl"]["ossSig"] = MIL_FILENAME
        if "dimModelUrls" in agent["model"]:
            for dim in agent["model"]["dimModelUrls"]:
                dim["url"] = rel_glb
                dim["ossSig"] = GLB_FILENAME

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump([agent], f, ensure_ascii=False, indent=2)
    print(f"[json] saved {output_json}")


def zip_package(model_root, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(model_root, "agent.json"), "agent.json")
        assets_root = os.path.join(model_root, MODEL_NAME)
        for file_name in sorted(os.listdir(assets_root)):
            p = os.path.join(assets_root, file_name)
            if os.path.isfile(p):
                zf.write(p, f"{MODEL_NAME}/{file_name}")
    print(f"[zip] saved {zip_path}")


def main():
    apply_proxy_env()
    models_dir = get_models_dir()
    model_root = os.path.join(models_dir, MODEL_NAME)
    assets_dir = os.path.join(model_root, MODEL_NAME)
    ensure_dir(assets_dir)

    thumb_png = os.path.join(assets_dir, PNG_FILENAME)
    mil_png = os.path.join(assets_dir, MIL_FILENAME)
    glb_path = os.path.join(assets_dir, GLB_FILENAME)
    agent_json = os.path.join(model_root, "agent.json")
    zip_path = os.path.join(models_dir, f"{MODEL_NAME}.zip")

    fetch_real_thumbnail(thumb_png)
    generate_military_symbol(mil_png)

    try:
        generate_glb_with_blendermcp(thumb_png, glb_path)
    except Exception as exc:
        print(f"[glb] BlenderMCP unavailable or missile generation failed, using fallback mesh: {exc}")
        export_fallback_glb(glb_path)

    normalize_missile_pose_glb(glb_path)
    if ENABLE_QUALITY_GATE and missile_quality_needs_fallback(glb_path):
        export_fallback_glb(glb_path)
        normalize_missile_pose_glb(glb_path)
        print("[glb] switched to fallback clean missile mesh after quality gate")
    generate_agent_json(agent_json)
    zip_package(model_root, zip_path)

    schema = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        "src",
        "校验代码参考",
        "AgentData_schema.json",
    )
    rc = validate_files(schema, [agent_json])
    if rc != 0:
        raise SystemExit(rc)
    print("[done] NSM package generated successfully.")


if __name__ == "__main__":
    main()
