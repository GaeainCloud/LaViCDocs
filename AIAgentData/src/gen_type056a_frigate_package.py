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

MODEL_NAME = "Type_056A_Frigate"
MODEL_NAME_I18N = "056A型护卫舰"
IMAGE_QUERY = "Type 056A frigate 3d render side view"
TEMPLATE_JSON = "05shipAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "中国056A型轻型护卫舰，具备近海巡逻、反潜反舰与编队护航作战能力。"
PREFERRED_IMAGE_URLS = [
    "https://cdn.renderhub.com/mermodels/594-zhuzhou-type-056a-jiangdao-class-corvette/594-zhuzhou-type-056a-jiangdao-class-corvette-04.jpg",
    "https://cdn.renderhub.com/mermodels/594-zhuzhou-type-056a-jiangdao-class-corvette/594-zhuzhou-type-056a-jiangdao-class-corvette-08.jpg",
    "https://cdn.renderhub.com/mermodels/594-zhuzhou-type-056a-jiangdao-class-corvette/594-zhuzhou-type-056a-jiangdao-class-corvette-02.jpg",
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
    good_kw = ("type 056a", "jiangdao", "corvette", "frigate", "surface combatant", "renderhub", "render", "3d")
    bad_kw = ("logo", "patch", "wallpaper", "diagram", "blueprint", "deck crew", "interior", "close", "tower")

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
            w, h = img.size
            if max(w, h) < 800:
                return
            score = (w * h) + (150000 if w > h else 0) + (200000 if any(k in lower for k in good_kw) else 0)
            if "594-zhuzhou-type-056a-jiangdao-class-corvette-04.jpg" in lower or "594-zhuzhou-type-056a-jiangdao-class-corvette-08.jpg" in lower or "594-zhuzhou-type-056a-jiangdao-class-corvette-02.jpg" in lower:
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
        raise RuntimeError("Failed to download a valid Type 056A frigate thumbnail image.")

    _, image, source_url, w, h = best
    image.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {source_url}")


def generate_military_symbol(output_png):
    svg = military_symbol.get_symbol_svg_string_from_name(
        "Friendly Destroyer", style="light", bounding_padding=4, use_variants=True
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
        raise RuntimeError("Failed to generate military symbol for Type 056A frigate.")

    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png}")


def build_carrier_mesh():
    hull_color = [165, 170, 176, 255]
    deck_color = [120, 124, 128, 255]
    dark = [80, 84, 90, 255]
    parts = []

    hull = trimesh.creation.box(extents=[7.8, 0.9, 0.82])
    hull.apply_translation([0.0, 0.0, 0.15])
    hull.visual.face_colors = hull_color
    parts.append(hull)

    bow = trimesh.creation.box(extents=[1.2, 0.78, 0.64])
    bow.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(28), [0, 0, 1]))
    bow.apply_translation([4.55, 0.0, 0.18])
    bow.visual.face_colors = hull_color
    parts.append(bow)

    deck = trimesh.creation.box(extents=[7.45, 0.84, 0.08])
    deck.apply_translation([0.0, 0.0, 0.68])
    deck.visual.face_colors = deck_color
    parts.append(deck)

    super_1 = trimesh.creation.box(extents=[1.55, 0.52, 0.58])
    super_1.apply_translation([-0.6, 0.0, 1.08])
    super_1.visual.face_colors = hull_color
    parts.append(super_1)

    super_2 = trimesh.creation.box(extents=[0.96, 0.42, 0.46])
    super_2.apply_translation([0.6, 0.0, 1.25])
    super_2.visual.face_colors = hull_color
    parts.append(super_2)

    mast = trimesh.creation.box(extents=[0.22, 0.18, 0.95])
    mast.apply_translation([0.25, 0.0, 1.95])
    mast.visual.face_colors = dark
    parts.append(mast)

    hangar = trimesh.creation.box(extents=[1.0, 0.58, 0.38])
    hangar.apply_translation([-3.05, 0.0, 0.98])
    hangar.visual.face_colors = hull_color
    parts.append(hangar)

    helo_deck = trimesh.creation.box(extents=[1.85, 0.84, 0.08])
    helo_deck.apply_translation([-3.45, 0.0, 0.72])
    helo_deck.visual.face_colors = deck_color
    parts.append(helo_deck)

    gun = trimesh.creation.box(extents=[0.38, 0.25, 0.18])
    gun.apply_translation([3.1, 0.0, 0.82])
    gun.visual.face_colors = dark
    parts.append(gun)

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
    text_prompt='Type 054A frigate, full ship, complete connected hull, frigate superstructure, realistic naval vessel, no detached parts, clean topology',
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
        raise RuntimeError("Rodin job timed out for Type 054A frigate.")

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
        print(f"[glb] BlenderMCP unavailable or carrier generation failed, using fallback mesh: {exc}")
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
    print("[done] Type 056A frigate package generated successfully.")


if __name__ == "__main__":
    main()
