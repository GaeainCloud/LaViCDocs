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
from evtol_profile import apply_evtol_mission_profile
from runtime_config import apply_proxy_env, get_models_dir
from validate_all import validate_files


MODEL_NAME = "UH-60M_Black_Hawk"
MODEL_NAME_I18N = "UH-60M直升机"
IMAGE_QUERY = "UH-60M Black Hawk 3d render side view"
TEMPLATE_JSON = "02aircraftAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "美制中型通用直升机，具备机降突击、人员输送与多用途支援能力。"
PREFERRED_IMAGE_URLS = [
    "https://img-new.cgtrader.com/items/28018/b68f5ebf49/uh60m-blackhawk-helicopter-3d-model-max-obj-3ds-fbx-c4d-lwo.jpg",
    "https://p.turbosquid.com/ts-thumb/GQ/KLYuLj/77/uh60m/jpg/1663965737/1920x1080/turn_fit_q99/730a447254f253fe5321a954767b26c225ef1f8a/uh60m-1.jpg",
    "https://www.renderhub.com/frezzy/sikorsky-uh-60-black-hawk-1/sikorsky-uh-60-black-hawk-1-04.jpg?1711608586",
]


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def fetch_real_thumbnail(output_png):
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in PREFERRED_IMAGE_URLS:
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code != 200 or len(r.content) < 30000:
                continue
            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 1000:
                continue
            img.save(output_png, "PNG")
            print(f"[thumbnail] saved {output_png} ({w}x{h})")
            print(f"[thumbnail] source {url}")
            return
        except Exception:
            continue

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
        raise RuntimeError("No Bing image candidates found for UH-60M.")

    best = None
    good_kw = ("uh-60m", "black hawk", "sikorsky", "helicopter", "utility")
    render_kw = ("render", "behance", "turbosquid", "free3d", "cgtrader", "png")
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
            score = (
                (w * h)
                + (100000 if w > h else 0)
                + (150000 if any(k in lower for k in good_kw) else 0)
                + (200000 if any(k in lower for k in render_kw) else 0)
            )
            if best is None or score > best[0]:
                best = (score, img, url, w, h)
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Failed to download a valid real UH-60M thumbnail image.")

    _, image, source_url, w, h = best
    image.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {source_url}")


def generate_military_symbol(output_png):
    svg = military_symbol.get_symbol_svg_string_from_name(
        "Friendly Rotary Wing", style="light", bounding_padding=4, use_variants=True
    )
    if svg is None:
        raise RuntimeError("Failed to generate military symbol for UH-60M.")

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

    fuselage = trimesh.creation.capsule(radius=0.42, height=5.8, count=[24, 24])
    fuselage.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    fuselage.visual.face_colors = body_color
    parts.append(fuselage)

    nose = trimesh.creation.icosphere(subdivisions=2, radius=0.45)
    nose.apply_scale([1.35, 0.95, 0.85])
    nose.apply_translation([3.2, 0.0, 0.05])
    nose.visual.face_colors = body_color
    parts.append(nose)

    tail_boom = trimesh.creation.box(extents=[2.0, 0.28, 0.32])
    tail_boom.apply_translation([-3.6, 0.0, 0.15])
    tail_boom.visual.face_colors = body_color
    parts.append(tail_boom)

    h_tail = trimesh.creation.box(extents=[0.35, 1.9, 0.08])
    h_tail.apply_translation([-4.6, 0.0, 0.55])
    h_tail.visual.face_colors = body_color
    parts.append(h_tail)

    v_tail = trimesh.creation.box(extents=[0.25, 0.1, 0.9])
    v_tail.apply_translation([-4.7, 0.0, 0.75])
    v_tail.visual.face_colors = body_color
    parts.append(v_tail)

    sponson_l = trimesh.creation.box(extents=[1.2, 0.4, 0.35])
    sponson_l.apply_translation([-0.8, 1.0, -0.15])
    sponson_l.visual.face_colors = body_color
    parts.append(sponson_l)
    sponson_r = sponson_l.copy()
    sponson_r.apply_translation([0.0, -2.0, 0.0])
    parts.append(sponson_r)

    mast = trimesh.creation.cylinder(radius=0.08, height=0.7, sections=20)
    mast.apply_translation([0.0, 0.0, 0.9])
    mast.visual.face_colors = dark
    parts.append(mast)

    for angle in [0, np.pi / 2, np.pi, 3 * np.pi / 2]:
        blade = trimesh.creation.box(extents=[4.8, 0.16, 0.03])
        blade.apply_translation([2.4, 0.0, 1.22])
        blade.apply_transform(trimesh.transformations.rotation_matrix(angle, [0, 0, 1]))
        blade.visual.face_colors = dark
        parts.append(blade)

    tail_rotor_hub = trimesh.creation.cylinder(radius=0.06, height=0.14, sections=16)
    tail_rotor_hub.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    tail_rotor_hub.apply_translation([-4.95, 0.0, 0.55])
    tail_rotor_hub.visual.face_colors = dark
    parts.append(tail_rotor_hub)

    for angle in [0, np.pi / 2]:
        tail_blade = trimesh.creation.box(extents=[0.7, 0.05, 0.03])
        tail_blade.apply_translation([-4.95, 0.0, 0.55])
        tail_blade.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        tail_blade.apply_transform(trimesh.transformations.rotation_matrix(angle, [0, 1, 0]))
        tail_blade.visual.face_colors = dark
        parts.append(tail_blade)

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
    text_prompt='UH-60M Black Hawk military utility helicopter, realistic hard-surface helicopter, full aircraft, modern utility rotorcraft, main rotor and tail rotor, high quality military helicopter',
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
        raise RuntimeError("Rodin job timed out for UH-60M.")

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
    apply_evtol_mission_profile(agent)

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
    print("[done] UH-60M package generated successfully.")


if __name__ == "__main__":
    main()
