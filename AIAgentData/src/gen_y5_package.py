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
    inspect_aircraft_mesh_quality,
    normalize_aircraft_heading_glb,
    prune_aircraft_loose_parts_glb,
)
from runtime_config import apply_proxy_env, get_models_dir
from validate_all import validate_files


MODEL_NAME = "Y-5_Light_Transport"
MODEL_NAME_I18N = "运-5运输机"
IMAGE_QUERY = "Harbin Y-5 Antonov An-2 transport biplane 3d render side view"
TEMPLATE_JSON = "02aircraftAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "中国轻型双翼运输机，适用于短距起降、轻型运输、联络支援与低空通航任务。"
PREFERRED_IMAGE_URLS = [
    "https://www.renderhub.com/be-gemot/antonov-an-2t/antonov-an-2t-01.jpg",
    "https://cdn.renderhub.com/be-gemot/antonov-an-2t/antonov-an-2t-20.jpg",
    "https://www.renderhub.com/be-gemot/gallery/antonov-an-2t-exterior_p.jpeg",
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
    good_kw = (
        "y-5",
        "y5",
        "an-2",
        "an2",
        "antonov",
        "harbin",
        "biplane",
        "transport",
        "aircraft",
    )
    render_kw = ("renderhub", "render", "cgtrader", "turbosquid", "exterior")
    bad_kw = (
        "logo",
        "patch",
        "wallpaper",
        "diagram",
        "blueprint",
        "interior",
        "cabin",
        "seat",
        "cockpit",
        "avionics",
    )

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
            score = (
                (w * h)
                + (120000 if w > h else 0)
                + (180000 if any(k in lower for k in good_kw) else 0)
                + (200000 if any(k in lower for k in render_kw) else 0)
            )
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

        if not candidates:
            raise RuntimeError("No Bing image candidates found for Y-5.")

        for url in candidates[:80]:
            consider(url)

    if best is None:
        raise RuntimeError("Failed to download a valid Y-5 thumbnail image.")

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
        raise RuntimeError("Failed to generate military symbol for Y-5.")

    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png}")


def build_biplane_mesh():
    body_color = [205, 205, 205, 255]
    dark = [70, 70, 70, 255]
    tire = [40, 40, 40, 255]
    parts = []

    fuselage = trimesh.creation.capsule(radius=0.20, height=3.9, count=[24, 24])
    fuselage.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    fuselage.visual.face_colors = body_color
    parts.append(fuselage)

    nose = trimesh.creation.cone(radius=0.18, height=0.45, sections=24)
    nose.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0]))
    nose.apply_translation([2.15, 0, 0.0])
    nose.visual.face_colors = body_color
    parts.append(nose)

    upper_wing = trimesh.creation.box(extents=[0.75, 4.6, 0.08])
    upper_wing.apply_translation([0.2, 0, 0.70])
    upper_wing.visual.face_colors = body_color
    parts.append(upper_wing)

    lower_wing = trimesh.creation.box(extents=[0.70, 4.0, 0.08])
    lower_wing.apply_translation([0.15, 0, -0.12])
    lower_wing.visual.face_colors = body_color
    parts.append(lower_wing)

    for x in (-0.25, 0.55):
        for side in (-1, 1):
            strut = trimesh.creation.cylinder(radius=0.03, height=0.88, sections=16)
            strut.apply_translation([x, side * 1.25, 0.29])
            strut.visual.face_colors = dark
            parts.append(strut)

    h_tail = trimesh.creation.box(extents=[0.35, 1.65, 0.06])
    h_tail.apply_translation([-1.85, 0, 0.25])
    h_tail.visual.face_colors = body_color
    parts.append(h_tail)

    v_tail = trimesh.creation.box(extents=[0.30, 0.06, 0.75])
    v_tail.apply_translation([-1.95, 0, 0.62])
    v_tail.visual.face_colors = body_color
    parts.append(v_tail)

    engine = trimesh.creation.cylinder(radius=0.18, height=0.35, sections=24)
    engine.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    engine.apply_translation([1.78, 0, 0.0])
    engine.visual.face_colors = dark
    parts.append(engine)

    hub = trimesh.creation.cylinder(radius=0.05, height=0.10, sections=16)
    hub.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    hub.apply_translation([2.02, 0, 0.0])
    hub.visual.face_colors = dark
    parts.append(hub)

    blade_a = trimesh.creation.box(extents=[0.04, 1.15, 0.08])
    blade_a.apply_translation([2.08, 0, 0.0])
    blade_a.visual.face_colors = dark
    parts.append(blade_a)

    blade_b = trimesh.creation.box(extents=[0.04, 0.08, 1.15])
    blade_b.apply_translation([2.08, 0, 0.0])
    blade_b.visual.face_colors = dark
    parts.append(blade_b)

    gear_axle = trimesh.creation.cylinder(radius=0.025, height=1.35, sections=14)
    gear_axle.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    gear_axle.apply_translation([0.55, 0, -0.48])
    gear_axle.visual.face_colors = dark
    parts.append(gear_axle)

    for side in (-1, 1):
        wheel = trimesh.creation.cylinder(radius=0.16, height=0.08, sections=20)
        wheel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        wheel.apply_translation([0.55, side * 0.70, -0.60])
        wheel.visual.face_colors = tire
        parts.append(wheel)

        leg = trimesh.creation.cylinder(radius=0.03, height=0.52, sections=14)
        leg.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(20), [0, 1, 0]))
        leg.apply_translation([0.45, side * 0.70, -0.30])
        leg.visual.face_colors = dark
        parts.append(leg)

    tail_wheel = trimesh.creation.cylinder(radius=0.07, height=0.05, sections=16)
    tail_wheel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    tail_wheel.apply_translation([-1.95, 0, -0.48])
    tail_wheel.visual.face_colors = tire
    parts.append(tail_wheel)

    return trimesh.util.concatenate(parts)


def export_fallback_glb(output_glb):
    mesh = build_biplane_mesh()
    scene = trimesh.Scene(mesh)
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
    text_prompt='Harbin Y-5 Antonov An-2 light utility transport biplane aircraft, full plane, complete connected airframe, realistic hard-surface aircraft, single propeller, upper and lower wings, no detached parts, clean topology',
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
        raise RuntimeError("Rodin job timed out for Y-5.")

    imported = client.call("import_generated_asset", {"task_uuid": task_uuid, "name": MODEL_NAME})
    if imported.get("status") != "success" or not imported.get("result", {}).get("succeed"):
        raise RuntimeError(f"Rodin import failed: {imported}")

    export_code = f"""
import bpy, os
import mathutils
name = '{MODEL_NAME}'
out = r'{output_glb}'
EXPORT_YUP = {str(BLENDER_AIRCRAFT_EXPORT_YUP)}
if EXPORT_YUP:
    raise RuntimeError('Aircraft GLB export must use export_yup=False for LaViC/three.js pipeline')
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

    used_fallback = False
    try:
        generate_glb_with_blendermcp(thumb_png, glb_path)
        normalize_aircraft_heading_glb(glb_path, AIRCRAFT_HEADING_NORMALIZATION_DEG)
        print(f"[glb] applied heading normalization Z {AIRCRAFT_HEADING_NORMALIZATION_DEG:+d}° -> {glb_path}")

        cleanup = prune_aircraft_loose_parts_glb(glb_path)
        print(
            f"[glb] pruned loose parts: kept {cleanup['kept_faces']} / {cleanup['total_faces']} faces across {cleanup['cluster_count']} clusters"
        )

        quality = inspect_aircraft_mesh_quality(glb_path)
        kept_ratio = (
            float(cleanup["kept_faces"]) / float(cleanup["total_faces"])
            if cleanup["total_faces"]
            else 0.0
        )
        print(
            "[glb] quality "
            f"faces={quality['faces']} length={quality['length']:.3f} span={quality['span']:.3f} "
            f"height={quality['height']:.3f} span_ratio={quality['span_ratio']:.3f} height_ratio={quality['height_ratio']:.3f} kept_ratio={kept_ratio:.3f}"
        )

        if (
            kept_ratio < 0.42
            or quality["faces"] < 1500
            or quality["span_ratio"] < 0.55
            or quality["height_ratio"] < 0.18
        ):
            print("[glb] generated Y-5 model incomplete, switching to complete biplane fallback mesh")
            export_fallback_glb(glb_path)
            used_fallback = True
    except Exception as exc:
        print(f"[glb] BlenderMCP unavailable or generation invalid, using fallback mesh: {exc}")
        export_fallback_glb(glb_path)
        used_fallback = True

    if used_fallback:
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
    print("[done] Y-5 package generated successfully.")


if __name__ == "__main__":
    main()
