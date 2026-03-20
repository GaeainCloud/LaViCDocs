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
from ship_orientation import (
    apply_known_ship_roll_override,
    get_ship_policy_summary,
    normalize_ship_pose_glb,
)
from validate_all import validate_files

MODEL_NAME = "Type_039AB_Submarine"
MODEL_NAME_I18N = "039A/B型潜艇"
IMAGE_QUERY = "Type 039A Yuan class submarine 3d render side view"
TEMPLATE_JSON = "04underwaterVehicleAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "039A/B型常规潜艇，具备AIP静音巡航、反舰反潜与近海隐蔽突防能力。"
PREFERRED_IMAGE_URLS = [
    "https://p.turbosquid.com/ts-thumb/f2/ZnYEKR/rk/yuanclass_military_submarine_type_039a_rigged_004/jpg/1751980221/1920x1080/fit_q87/59aeed5d54cc71dddec42b2c51f6606b5f9c6e72/yuanclass_military_submarine_type_039a_rigged_004.jpg",
    "https://p.turbosquid.com/ts-thumb/f2/ZnYEKR/Ny/yuanclass_military_submarine_type_039a_rigged_003/jpg/1751980217/1920x1080/fit_q87/aa3b35b5681039590d2304a0886930a4a077cc33/yuanclass_military_submarine_type_039a_rigged_003.jpg",
    "https://p.turbosquid.com/ts-thumb/f2/ZnYEKR/gU/yuanclass_military_submarine_type_039a_rigged_005/jpg/1751980224/1920x1080/fit_q87/761a3249db3fe51831b86c1c9ac2f52e5c8d1105/yuanclass_military_submarine_type_039a_rigged_005.jpg",
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
    good_kw = ("039a", "039b", "yuan", "submarine", "render", "3d", "turbosquid", "chinese")
    bad_kw = (
        "logo",
        "patch",
        "wallpaper",
        "diagram",
        "blueprint",
        "deck crew",
        "interior",
        "close",
        "tower",
        "texture",
        "material",
        "uv",
        "albedo",
        "normal",
        "roughness",
        "metallic",
        "sheet",
        "atlas",
        "janes",
        "satellite",
        "huludao",
        "sky",
        "shipyard",
        "planet",
        "analysis",
    )

    def normalize_thumbnail(img):
        arr = np.asarray(img)
        mask = arr.sum(axis=2) > 45
        ys, xs = np.where(mask)
        if len(xs) and len(ys):
            x0, x1 = xs.min(), xs.max()
            y0, y1 = ys.min(), ys.max()
            pad_x = max(20, int((x1 - x0 + 1) * 0.08))
            pad_y = max(20, int((y1 - y0 + 1) * 0.12))
            x0 = max(0, x0 - pad_x)
            y0 = max(0, y0 - pad_y)
            x1 = min(img.width, x1 + pad_x)
            y1 = min(img.height, y1 + pad_y)
            img = img.crop((x0, y0, x1, y1))

        canvas = Image.new("RGB", (1400, 900), "white")
        img.thumbnail((1280, 780))
        canvas.paste(img, ((canvas.width - img.width) // 2, (canvas.height - img.height) // 2))
        return canvas

    def clean_specific_source(img, lower):
        # Prefer a clean single-submarine crop when the source image contains
        # foreground deck clutter or text overlays.
        if "yuanclass_military_submarine_type_039a_rigged_004.jpg" in lower:
            w, h = img.size
            img = img.crop((int(w * 0.02), int(h * 0.18), int(w * 0.78), int(h * 0.82)))
        elif "yuanclass_military_submarine_type_039a_rigged_003.jpg" in lower:
            w, h = img.size
            img = img.crop((int(w * 0.10), int(h * 0.18), int(w * 0.92), int(h * 0.62)))
        return img

    def consider(url, strict_size=True):
        nonlocal best
        lower = url.lower()
        if any(k in lower for k in bad_kw):
            return
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return
            if strict_size and len(r.content) < 20000:
                return
            img = Image.open(BytesIO(r.content)).convert("RGB")
            img = clean_specific_source(img, lower)
            w, h = img.size
            if max(w, h) < 800:
                return
            score = (w * h) + (150000 if w > h else 0) + (200000 if any(k in lower for k in good_kw) else 0)
            if "yuanclass_military_submarine_type_039a_rigged_004.jpg" in lower:
                score += 900000
            elif "yuanclass_military_submarine_type_039a_rigged_003.jpg" in lower:
                score += 700000
            elif "yuanclass_military_submarine_type_039a_rigged_005.jpg" in lower:
                score += 500000
            elif "039a" in lower or "039b" in lower or "yuan" in lower or "submarine" in lower:
                score += 300000
            if best is None or score > best[0]:
                best = (score, normalize_thumbnail(img), url, w, h)
        except Exception:
            return

    for url in PREFERRED_IMAGE_URLS:
        consider(url, strict_size=False)
        if best is not None:
            _, image, source_url, w, h = best
            image.save(output_png, "PNG")
            print(f"[thumbnail] saved {output_png} ({w}x{h})")
            print(f"[thumbnail] source {source_url}")
            return

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
        raise RuntimeError("Failed to download a valid Type 039A/B submarine thumbnail image.")

    _, image, source_url, w, h = best
    image.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {source_url}")


def generate_military_symbol(output_png):
    svg = military_symbol.get_symbol_svg_string_from_name(
        "Friendly Submarine", style="light", bounding_padding=4, use_variants=True
    )
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Friendly Surface Combatant", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Friendly Surface Ship", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        raise RuntimeError("Failed to generate military symbol for Type 039A/B submarine.")

    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png}")


def build_submarine_mesh():
    hull_color = [120, 126, 132, 255]
    dark = [70, 76, 84, 255]
    parts = []

    hull = trimesh.creation.capsule(radius=0.32, height=6.6, count=[32, 32])
    hull.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    hull.apply_translation([0.0, 0.0, 0.32])
    hull.visual.face_colors = hull_color
    parts.append(hull)

    sail = trimesh.creation.box(extents=[0.9, 0.18, 0.58])
    sail.apply_translation([0.35, 0.0, 0.78])
    sail.visual.face_colors = dark
    parts.append(sail)

    fairwater = trimesh.creation.box(extents=[0.45, 0.12, 0.18])
    fairwater.apply_translation([0.58, 0.0, 1.06])
    fairwater.visual.face_colors = dark
    parts.append(fairwater)

    stern_fin_v = trimesh.creation.box(extents=[0.12, 0.04, 0.68])
    stern_fin_v.apply_translation([-3.45, 0.0, 0.42])
    stern_fin_v.visual.face_colors = dark
    parts.append(stern_fin_v)

    stern_fin_h = trimesh.creation.box(extents=[0.12, 0.58, 0.04])
    stern_fin_h.apply_translation([-3.45, 0.0, 0.42])
    stern_fin_h.visual.face_colors = dark
    parts.append(stern_fin_h)

    planes = trimesh.creation.box(extents=[0.38, 0.86, 0.04])
    planes.apply_translation([0.95, 0.0, 0.54])
    planes.visual.face_colors = dark
    parts.append(planes)

    return trimesh.util.concatenate(parts)

def export_fallback_glb(output_glb):
    mesh = build_submarine_mesh()
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
    text_prompt='Type 039A/B Yuan class AIP submarine, complete connected submarine hull, integrated sail, conventional attack submarine proportions, clean side profile, no detached parts, no floating geometry, clean topology',
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
        raise RuntimeError("Rodin job timed out for Type 039A/B submarine.")

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
        print(f"[glb] BlenderMCP unavailable or submarine generation failed, using fallback mesh: {exc}")
        export_fallback_glb(glb_path)

    pose = normalize_ship_pose_glb(glb_path)
    print(
        "[glb] normalized ship pose "
        f"(leveled={pose['leveled']}, rolled={pose['rolled']}, heading_fixed={pose['heading_fixed']}, extents={pose['extents']}) -> {glb_path}"
    )
    override_applied, override_deg = apply_known_ship_roll_override(glb_path, MODEL_NAME)
    if override_applied:
        print(f"[glb] applied shared ship roll override X {override_deg:+d}° -> {glb_path}")

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
    print("[done] Type 039A/B submarine package generated successfully.")


if __name__ == "__main__":
    main()
