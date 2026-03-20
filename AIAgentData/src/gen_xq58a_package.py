import copy
import json
import os
import re
import socket
import time
import uuid
import zipfile
from io import BytesIO

import numpy as np
import requests
import trimesh
from PIL import Image, ImageDraw
from trimesh.geometry import align_vectors

from runtime_config import apply_proxy_env, get_models_dir
from validate_all import validate_files


MODEL_NAME = "XQ_58A_Loyal_Wingman"
MODEL_NAME_I18N = "XQ-58A僚机"
IMAGE_QUERY = "XQ-58A Valkyrie loyal wingman drone side view"
TEMPLATE_JSON = "06loiterMunitionAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "XQ-58A Valkyrie隐身僚机/忠诚僚机平台，可执行协同侦察、伴随突防与自主打击任务。"
PREFERRED_IMAGE_URLS = [
    "https://afresearchlab.com/wp-content/uploads/2020/09/Valkyrie-scaled-e1709836576731.jpg",
    "https://www.airandspaceforces.com/app/uploads/2021/10/Kratos_XQ58A_F35_F22-1000x676.jpg",
    "https://cdn.renderhub.com/akela-freedom/xq-58-valkyrie/xq-58-valkyrie-10.jpg",
]


def ensure_dir(path: str) -> None:
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
            return json.loads(b"".join(chunks).decode("utf-8", "replace"))
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
        f"raw={json.dumps(submit_json, ensure_ascii=False)[:1200]}"
    )


def normalize_thumbnail(img: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1400, 900), "white")
    img.thumbnail((1280, 760))
    canvas.paste(img, ((canvas.width - img.width) // 2, (canvas.height - img.height) // 2))
    return canvas


def fetch_real_thumbnail(output_png: str) -> None:
    headers = {"User-Agent": "Mozilla/5.0"}

    def prepare_img(url: str, content: bytes):
        img = Image.open(BytesIO(content)).convert("RGB")
        w, h = img.size
        if max(w, h) < 800:
            return None
        lower = url.lower()
        return normalize_thumbnail(img), w, h

    # Strongly prefer clean single-equipment sources first.
    for url in PREFERRED_IMAGE_URLS:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.content) < 15000:
                continue
            prepared = prepare_img(url, r.content)
            if prepared is None:
                continue
            img, w, h = prepared
            img.save(output_png, "PNG")
            print(f"[thumbnail] saved {output_png} ({w}x{h})")
            print(f"[thumbnail] source {url}")
            return
        except Exception:
            continue

    candidates = []
    resp = requests.get(
        "https://www.bing.com/images/search",
        params={"q": IMAGE_QUERY, "qft": "filterui:imagesize-large"},
        headers=headers,
        timeout=20,
    )
    resp.raise_for_status()
    html = resp.text
    murls = re.findall(r'"murl":"(.*?)"', html) or re.findall(r"murl&quot;:&quot;(.*?)&quot;", html)
    for raw in murls:
        url = raw.encode("utf-8").decode("unicode_escape").replace("\/", "/")
        if url not in candidates:
            candidates.append(url)

    good_kw = ("xq-58", "valkyrie", "kratos", "loyal", "wingman", "drone", "ucav")
    bad_kw = ("logo", "icon", "patch", "poster", "wallpaper", "drawing", "pilot", "cockpit", "soldier", "troop", "formation")
    best = None

    for url in candidates[:120]:
        lower = url.lower()
        if any(k in lower for k in bad_kw):
            continue
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.content) < 15000:
                continue
            prepared = prepare_img(url, r.content)
            if prepared is None:
                continue
            img, w, h = prepared
            ratio = w / max(h, 1)
            ratio_score = 120000 if 1.2 <= ratio <= 2.8 else 0
            kw_score = 220000 if any(k in lower for k in good_kw) else 0
            score = (w * h) + ratio_score + kw_score
            if "kratosdefense" in lower or "xq-58a_valkyrie" in lower:
                score += 500000
            if best is None or score > best[0]:
                best = (score, img, url, w, h)
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Failed to download a valid XQ-58A thumbnail.")

    _, img, src, w, h = best
    img.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {src}")


def generate_blue_military_symbol(output_png: str) -> None:
    # Draw a friendly blue frame with a simple UCAV-like aircraft glyph.
    size = 160
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    blue = (72, 132, 255, 255)
    black = (16, 16, 16, 255)

    # Friendly frame
    pad = 14
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=10,
        outline=blue,
        width=8,
        fill=(255, 255, 255, 235),
    )

    # UCAV-like body and wings
    draw.polygon([(44, 80), (66, 70), (108, 70), (118, 80), (108, 90), (66, 90)], fill=black)
    draw.polygon([(70, 79), (46, 58), (62, 79)], fill=black)
    draw.polygon([(70, 81), (46, 102), (62, 81)], fill=black)
    draw.polygon([(94, 78), (82, 62), (90, 78)], fill=black)
    draw.polygon([(94, 82), (82, 98), (90, 82)], fill=black)

    img.save(output_png, "PNG")
    print(f"[symbol] saved {output_png} (blue/friendly)")


def build_switchblade_mesh() -> trimesh.Trimesh:
    gray = [214, 214, 214, 255]
    dark = [170, 170, 170, 255]
    parts = []

    fuselage = trimesh.creation.capsule(radius=0.10, height=1.10, count=[16, 24])
    fuselage.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
    fuselage.visual.face_colors = gray
    parts.append(fuselage)

    wing = trimesh.creation.box(extents=[0.35, 1.45, 0.04])
    wing.apply_translation([0.05, 0.0, 0.0])
    wing.visual.face_colors = dark
    parts.append(wing)

    canard = trimesh.creation.box(extents=[0.16, 0.55, 0.03])
    canard.apply_translation([0.48, 0.0, 0.03])
    canard.visual.face_colors = dark
    parts.append(canard)

    vtail_l = trimesh.creation.box(extents=[0.22, 0.04, 0.42])
    vtail_l.apply_transform(trimesh.transformations.rotation_matrix(np.radians(28), [1, 0, 0]))
    vtail_l.apply_translation([-0.46, -0.20, 0.18])
    vtail_l.visual.face_colors = dark
    parts.append(vtail_l)

    vtail_r = trimesh.creation.box(extents=[0.22, 0.04, 0.42])
    vtail_r.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-28), [1, 0, 0]))
    vtail_r.apply_translation([-0.46, 0.20, 0.18])
    vtail_r.visual.face_colors = dark
    parts.append(vtail_r)

    return trimesh.util.concatenate(parts)


def apply_orientation_fix(scene: trimesh.Scene) -> None:
    # skill.md strict order:
    # 1) X -90 (Z-up -> Y-up)
    # 2) Y 180  (facing correction)
    rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
    scene.apply_transform(rot_x)
    rot_y = trimesh.transformations.rotation_matrix(np.radians(180), [0, 1, 0])
    scene.apply_transform(rot_y)


def normalize_loiter_pose_glb(glb_path: str) -> None:
    scene = trimesh.load(glb_path, force="scene")
    mesh = scene.to_geometry()
    forward = mesh.principal_inertia_vectors[0]
    scene.apply_transform(align_vectors(forward, [1, 0, 0]))

    # Aircraft-like loiter platform should lie flat with wing span on Y, not stand on Z.
    extents = scene.bounds[1] - scene.bounds[0]
    rolled = False
    if extents[2] > extents[1]:
        scene.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2.0, [1, 0, 0]))
        rolled = True

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
    print(f"[glb] normalized loiter pose rolled={rolled} extents={extents.tolist()} -> {glb_path}")


def generate_glb_with_blendermcp(image_path: str, output_glb: str) -> None:
    client = BlenderMCPClient()
    scene_info = client.call("get_scene_info")
    if scene_info.get("status") != "success":
        raise RuntimeError(f"BlenderMCP scene check failed: {scene_info}")

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
    text_prompt='XQ-58A Valkyrie loyal wingman drone, single complete aircraft, stealth unmanned combat aerial vehicle, blended fuselage, pointed nose, mid-mounted swept wings, canted tail surfaces, ventral air intake, no pilot, no launcher, no detached parts, no floating geometry, clean topology, clean side profile',
    images=[('.png', img_bytes)]
)
print('RESP_JSON_START')
print(json.dumps(resp))
print('RESP_JSON_END')
"""
    submit = client.call("execute_code", {"code": submit_code})
    result_text = (submit.get("result") or {}).get("result", "")
    submit_json = parse_json_between_markers(result_text, "RESP_JSON_START", "RESP_JSON_END")
    task_uuid, subscription_key = extract_rodin_submit_info(submit_json)

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
        raise RuntimeError("Rodin job timed out for XQ-58A.")

    imported = client.call("import_generated_asset", {"task_uuid": task_uuid, "name": MODEL_NAME})
    if imported.get("status") != "success" or not imported.get("result", {}).get("succeed"):
        raise RuntimeError(f"Rodin import failed: {imported}")

    export_code = f"""
import bpy, os, mathutils
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


def generate_glb(output_glb: str) -> None:
    mesh = build_switchblade_mesh()
    scene = trimesh.Scene(mesh)
    apply_orientation_fix(scene)
    glb = trimesh.exchange.gltf.export_glb(scene)
    with open(output_glb, "wb") as f:
        f.write(glb)
    print(f"[glb] saved {output_glb}")


def generate_agent_json(output_json: str) -> None:
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
    agent["agentKeyword"] = "xq58a"

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


def zip_package(model_root: str, zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(model_root, "agent.json"), "agent.json")
        assets_root = os.path.join(model_root, MODEL_NAME)
        for file_name in sorted(os.listdir(assets_root)):
            p = os.path.join(assets_root, file_name)
            if os.path.isfile(p):
                zf.write(p, f"{MODEL_NAME}/{file_name}")
    print(f"[zip] saved {zip_path}")


def main() -> None:
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
    generate_blue_military_symbol(mil_png)
    try:
        generate_glb_with_blendermcp(thumb_png, glb_path)
    except Exception as exc:
        print(f"[glb] BlenderMCP unavailable or loiter-munition generation failed, using fallback mesh: {exc}")
        generate_glb(glb_path)
    normalize_loiter_pose_glb(glb_path)
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
    print("[done] XQ-58A package generated successfully.")


if __name__ == "__main__":
    main()
