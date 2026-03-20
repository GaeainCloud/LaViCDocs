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

from runtime_config import apply_proxy_env, get_models_dir
from ship_orientation import get_ship_policy_summary, normalize_ship_pose_glb
from validate_all import validate_files

MODEL_NAME = "Liaoning_Aircraft_Carrier"
MODEL_NAME_I18N = "辽宁舰"
IMAGE_QUERY = "Liaoning aircraft carrier 3d render side view"
TEMPLATE_JSON = "05shipAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "中国首艘滑跃起飞型航空母舰，具备舰载机起降保障、编队指挥与远海综合作战能力。"
POST_ROLL_OVERRIDE_X_DEG = 90
PREFERRED_IMAGE_URLS = [
    "https://www.mechstream.com/wp-content/uploads/2025/03/Liaoning-Aircraft-Carrier-Including-Carrier-Based-Aircraft.png",
    "https://www.mechstream.com/wp-content/uploads/2025/03/Liaoning-Aircraft-Carrier-Model-840x400.png",
    "https://media.sketchfab.com/models/afb19cc2c8484fb9ab32672ae77802ff/thumbnails/2b2db913054d4bd28f247f7536cb0ac2/01a8bc2312794deab0fd7ef8da05622c.jpeg",
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
            data = sock.recv(2_000_000).decode("utf-8", "replace")
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


def fetch_real_thumbnail(output_png):
    headers = {"User-Agent": "Mozilla/5.0"}
    best = None
    good_kw = ("liaoning", "carrier", "aircraft carrier", "render", "sketchfab", "mechstream")
    bad_kw = ("logo", "patch", "wallpaper", "diagram", "blueprint", "interior")

    def consider(url):
        nonlocal best
        lower = url.lower()
        if any(k in lower for k in bad_kw):
            return
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.content) < 20000:
                return
            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 800:
                return
            score = (w * h) + (150000 if w > h else 0) + (200000 if any(k in lower for k in good_kw) else 0)
            if best is None or score > best[0]:
                best = (score, img, url, w, h)
        except Exception:
            return

    for url in PREFERRED_IMAGE_URLS:
        consider(url)

    if best is None:
        resp = requests.get(
            "https://www.bing.com/images/search",
            params={"q": IMAGE_QUERY, "qft": "filterui:imagesize-large"},
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.text
        murls = re.findall(r'"murl":"(.*?)"', text) or re.findall(r"murl&quot;:&quot;(.*?)&quot;", text)
        candidates = []
        for raw in murls:
            url = raw.encode("utf-8").decode("unicode_escape").replace("\\/", "/")
            if url not in candidates:
                candidates.append(url)
        for url in candidates[:80]:
            consider(url)

    if best is None:
        raise RuntimeError("Failed to download a valid Liaoning carrier thumbnail image.")

    _, image, source_url, w, h = best
    image.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {source_url}")


def generate_military_symbol(output_png):
    svg = military_symbol.get_symbol_svg_string_from_name(
        "Friendly Aircraft Carrier", style="light", bounding_padding=4, use_variants=True
    )
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Friendly Surface Ship", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        raise RuntimeError("Failed to generate military symbol for Liaoning carrier.")

    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png}")


def build_carrier_mesh():
    hull_color = [170, 175, 180, 255]
    deck_color = [105, 110, 115, 255]
    dark = [75, 78, 82, 255]
    parts = []

    hull = trimesh.creation.box(extents=[8.4, 1.45, 1.10])
    hull.apply_translation([0.0, 0.0, 0.33])
    hull.visual.face_colors = hull_color
    parts.append(hull)

    bow = trimesh.creation.box(extents=[1.15, 1.15, 0.90])
    bow.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(34), [0, 0, 1]))
    bow.apply_translation([4.25, 0.0, 0.30])
    bow.visual.face_colors = hull_color
    parts.append(bow)

    stern = trimesh.creation.box(extents=[0.85, 1.30, 0.80])
    stern.apply_translation([-4.35, 0.0, 0.28])
    stern.visual.face_colors = hull_color
    parts.append(stern)

    deck = trimesh.creation.box(extents=[8.8, 2.0, 0.12])
    deck.apply_translation([0.0, 0.10, 0.98])
    deck.visual.face_colors = deck_color
    parts.append(deck)

    ski_jump = trimesh.creation.box(extents=[1.6, 2.0, 0.12])
    ski_jump.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(-16), [0, 1, 0]))
    ski_jump.apply_translation([3.65, 0.12, 1.20])
    ski_jump.visual.face_colors = deck_color
    parts.append(ski_jump)

    angled = trimesh.creation.box(extents=[3.0, 0.9, 0.10])
    angled.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(8), [0, 0, 1]))
    angled.apply_translation([-0.1, 0.88, 1.02])
    angled.visual.face_colors = deck_color
    parts.append(angled)

    island_base = trimesh.creation.box(extents=[0.95, 0.42, 0.70])
    island_base.apply_translation([-1.15, -0.48, 1.32])
    island_base.visual.face_colors = hull_color
    parts.append(island_base)

    island_top = trimesh.creation.box(extents=[0.55, 0.26, 0.40])
    island_top.apply_translation([-0.92, -0.46, 1.84])
    island_top.visual.face_colors = hull_color
    parts.append(island_top)

    mast = trimesh.creation.box(extents=[0.14, 0.12, 0.68])
    mast.apply_translation([-0.78, -0.45, 2.34])
    mast.visual.face_colors = dark
    parts.append(mast)

    return trimesh.util.concatenate(parts)


def export_fallback_glb(output_glb):
    mesh = build_carrier_mesh()
    scene = trimesh.Scene(mesh)
    with open(output_glb, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))
    print(f"[glb] fallback saved {output_glb}")
    print(f"[policy] {get_ship_policy_summary()}")


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
    text_prompt='Liaoning aircraft carrier, full ship, complete connected hull, ski-jump flight deck, island superstructure starboard side, realistic naval vessel, no detached parts, clean topology',
    images=[('.png', img_bytes)]
)
print('RESP_JSON_START')
print(json.dumps(resp))
print('RESP_JSON_END')
"""
    submit = client.call("execute_code", {"code": submit_code})
    result_text = submit["result"]["result"]
    submit_json = parse_json_between_markers(result_text, "RESP_JSON_START", "RESP_JSON_END")
    task_uuid = submit_json["uuid"]
    subscription_key = submit_json["jobs"]["subscription_key"]

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
        raise RuntimeError("Rodin job timed out for Liaoning carrier.")

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
    print(f"[policy] {get_ship_policy_summary()}")


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


def apply_manual_x_rotation(glb_path, degrees):
    if not degrees:
        return
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
    print(f"[glb] applied ski-jump carrier manual X rotation {degrees:+d}° -> {glb_path}")


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
        print(f"[glb] BlenderMCP unavailable or carrier generation failed, using fallback mesh: {exc}")
        export_fallback_glb(glb_path)

    pose = normalize_ship_pose_glb(glb_path)
    print(
        "[glb] normalized ship pose "
        f"(leveled={pose['leveled']}, rolled={pose['rolled']}, heading_fixed={pose['heading_fixed']}, extents={pose['extents']}) -> {glb_path}"
    )
    apply_manual_x_rotation(glb_path, POST_ROLL_OVERRIDE_X_DEG)

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
    print("[done] Liaoning carrier package generated successfully.")


if __name__ == "__main__":
    main()
