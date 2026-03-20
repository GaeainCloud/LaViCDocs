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

from aircraft_orientation import (
    AIRCRAFT_HEADING_NORMALIZATION_DEG,
    BLENDER_AIRCRAFT_EXPORT_YUP,
    assert_blender_aircraft_export_policy,
    get_aircraft_policy_summary,
    normalize_aircraft_heading_glb,
)
from runtime_config import apply_proxy_env, get_models_dir
from validate_all import validate_files


MODEL_NAME = "C-130J_Super_Hercules"
MODEL_NAME_I18N = "C-130J超级大力神运输机"
IMAGE_QUERY = "Lockheed Martin C-130J Super Hercules 3d render side view"
TEMPLATE_JSON = "02aircraftAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "美国四发涡桨中型战术运输机，具备战术空运、空投与多用途改装能力。"


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def fetch_real_thumbnail(output_png):
    headers = {"User-Agent": "Mozilla/5.0"}
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

    if not candidates:
        raise RuntimeError("No Bing image candidates found for C-130J.")

    best = None
    good_kw = ("c-130", "c130", "hercules", "super hercules", "lockheed", "transport", "aircraft")
    bad_kw = ("logo", "patch", "wallpaper", "diagram", "blueprint")
    for url in candidates[:80]:
        lower = url.lower()
        if any(k in lower for k in bad_kw):
            continue
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.content) < 20000:
                continue
            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 800:
                continue
            score = (w * h) + (100000 if w > h else 0) + (150000 if any(k in lower for k in good_kw) else 0)
            if best is None or score > best[0]:
                best = (score, img, url, w, h)
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Failed to download a valid real C-130J thumbnail image.")

    _, image, source_url, w, h = best
    image.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {source_url}")


def generate_military_symbol(output_png):
    svg = military_symbol.get_symbol_svg_string_from_name(
        "Friendly Cargo Aircraft", style="light", bounding_padding=4, use_variants=True
    )
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Friendly Fixed Wing", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        raise RuntimeError("Failed to generate military symbol for C-130J.")

    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png}")


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


def build_transport_mesh():
    # Fallback only when BlenderMCP is unavailable.
    parts = []
    body_color = [205, 205, 205, 255]
    dark = [70, 70, 70, 255]

    fuselage = trimesh.creation.capsule(radius=0.48, height=7.4, count=[24, 24])
    fuselage.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    fuselage.visual.face_colors = body_color
    parts.append(fuselage)

    wing = trimesh.creation.box(extents=[0.55, 7.8, 0.14])
    wing.apply_translation([0.4, 0, 0.35])
    wing.visual.face_colors = body_color
    parts.append(wing)

    h_tail = trimesh.creation.box(extents=[0.4, 2.8, 0.1])
    h_tail.apply_translation([-3.35, 0, 0.75])
    h_tail.visual.face_colors = body_color
    parts.append(h_tail)

    v_tail = trimesh.creation.box(extents=[0.35, 0.12, 1.35])
    v_tail.apply_translation([-3.5, 0, 1.2])
    v_tail.visual.face_colors = body_color
    parts.append(v_tail)

    for x in [0.95, 0.05]:
        for side in [-1, 1]:
            eng = trimesh.creation.cylinder(radius=0.22, height=0.85, sections=24)
            eng.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
            eng.apply_translation([x, side * 1.9, -0.02])
            eng.visual.face_colors = dark
            parts.append(eng)

    return trimesh.util.concatenate(parts)


def export_fallback_glb(output_glb):
    mesh = build_transport_mesh()
    scene = trimesh.Scene(mesh)
    # The fallback transport mesh is authored directly in the LaViC aircraft canonical pose.
    with open(output_glb, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))
    print(f"[glb] fallback saved {output_glb}")
    print(f"[policy] {get_aircraft_policy_summary()}")


def generate_glb_with_blendermcp(image_path, output_glb):
    assert_blender_aircraft_export_policy(BLENDER_AIRCRAFT_EXPORT_YUP)
    client = BlenderMCPClient()

    scene_info = client.call("get_scene_info")
    if scene_info.get("status") != "success":
        raise RuntimeError(f"BlenderMCP scene check failed: {scene_info}")

    hyper = client.call("get_hyper3d_status")
    if hyper.get("status") != "success" or not hyper.get("result", {}).get("enabled"):
        raise RuntimeError(f"Hyper3D not ready: {hyper}")

    # Clean default scene and submit Rodin job from local reference image.
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
    text_prompt='Lockheed Martin C-130J Super Hercules military transport aircraft, realistic hard-surface aircraft, full plane, high quality turboprop transport airplane',
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
        raise RuntimeError("Rodin job timed out for C-130J.")

    imported = client.call("import_generated_asset", {"task_uuid": task_uuid, "name": MODEL_NAME})
    if imported.get("status") != "success" or not imported.get("result", {}).get("succeed"):
        raise RuntimeError(f"Rodin import failed: {imported}")

    export_code = f"""
import bpy, os, math
import mathutils
name = '{MODEL_NAME}'
out = r'{output_glb}'
EXPORT_YUP = {str(BLENDER_AIRCRAFT_EXPORT_YUP)}
if EXPORT_YUP:
    raise RuntimeError('Aircraft GLB export must use export_yup=False for LaViC/three.js pipeline')
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
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
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=EXPORT_YUP)
print('EXPORTED', out)
"""
    exported = client.call("execute_code", {"code": export_code})
    if exported.get("status") != "success":
        raise RuntimeError(f"Blender export failed: {exported}")
    print(f"[glb] rodin saved {output_glb}")
    print(f"[policy] {get_aircraft_policy_summary()}")


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
        print(f"[glb] BlenderMCP unavailable, using fallback mesh: {exc}")
        export_fallback_glb(glb_path)

    normalize_aircraft_heading_glb(glb_path, AIRCRAFT_HEADING_NORMALIZATION_DEG)
    print(f"[glb] applied heading normalization Z {AIRCRAFT_HEADING_NORMALIZATION_DEG:+d}° -> {glb_path}")

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
    print("[done] C-130J package generated successfully.")


if __name__ == "__main__":
    main()
