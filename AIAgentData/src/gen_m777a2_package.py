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
from trimesh.geometry import align_vectors

from runtime_config import apply_proxy_env, get_models_dir
from validate_all import validate_files

MODEL_NAME = "M777A2_155mm_Howitzer"
MODEL_NAME_I18N = "M777A2 155mm榴弹炮"
IMAGE_QUERY = "M777A2 155mm howitzer side view render"
TEMPLATE_JSON = "08boundingMineAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "M777A2 155mm榴弹炮模型，采用抛物弹道动力学用于火炮射击与弹道打击仿真。"
PREFERRED_IMAGE_URLS = [
    "https://preview.free3d.com/img/2014/02/2408155673838749617/dn3g8pje.jpg",
    "https://www.armyrecognition.com/templates/yootheme/cache/3f/BAE_Systems_displays_M777_A2_Lightweight_155mm_Towed_Howitzer-3f8187d1.jpeg",
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
    good_kw = ("m777", "howitzer", "artillery", "155mm")
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
        "cockpit",
        "satellite",
        "janes",
        "analysis",
        "poster",
        "cults3d",
        "dreamstime",
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
            if strict_size and len(r.content) < 15000:
                return
            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if strict_size and max(w, h) < 700:
                return
            if (not strict_size) and max(w, h) < 500:
                return
            ratio = w / max(h, 1)
            score = (w * h) + (240000 if any(k in lower for k in good_kw) else 0)
            if 1.0 <= ratio <= 2.5:
                score += 120000
            if "dn3g8pje.jpg" in lower:
                score += 1000000
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
        raise RuntimeError("Failed to download a valid M777A2 thumbnail image.")

    _, image, source_url, w, h = best
    image.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {source_url}")


def generate_military_symbol(output_png):
    candidates = [
        "Friendly Howitzer",
        "Friendly Field Artillery",
        "Friendly Artillery",
        "Friendly Cannon",
    ]
    svg = None
    for name in candidates:
        svg = military_symbol.get_symbol_svg_string_from_name(
            name, style="light", bounding_padding=4, use_variants=True
        )
        if svg:
            break
    if svg is None:
        raise RuntimeError("Failed to generate military symbol for M777A2 howitzer.")
    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png}")


def build_howitzer_mesh():
    olive = [118, 125, 92, 255]
    dark = [88, 92, 70, 255]
    tire = [40, 40, 40, 255]
    metal = [150, 150, 150, 255]
    parts = []

    barrel = trimesh.creation.cylinder(radius=0.07, height=4.3, sections=32)
    barrel.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    barrel.apply_translation([1.8, 0.0, 0.95])
    barrel.visual.face_colors = metal
    parts.append(barrel)

    muzzle = trimesh.creation.cylinder(radius=0.09, height=0.2, sections=24)
    muzzle.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    muzzle.apply_translation([4.0, 0.0, 0.95])
    muzzle.visual.face_colors = dark
    parts.append(muzzle)

    cradle = trimesh.creation.box(extents=[1.3, 0.5, 0.4])
    cradle.apply_translation([0.8, 0.0, 0.8])
    cradle.visual.face_colors = olive
    parts.append(cradle)

    breech = trimesh.creation.box(extents=[0.55, 0.42, 0.42])
    breech.apply_translation([-0.05, 0.0, 0.85])
    breech.visual.face_colors = dark
    parts.append(breech)

    shield = trimesh.creation.box(extents=[0.18, 1.45, 0.95])
    shield.apply_translation([-0.45, 0.0, 1.0])
    shield.visual.face_colors = olive
    parts.append(shield)

    axle = trimesh.creation.cylinder(radius=0.05, height=1.25, sections=24)
    axle.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [1, 0, 0]))
    axle.apply_translation([-0.15, 0.0, 0.48])
    axle.visual.face_colors = dark
    parts.append(axle)

    for y in (-0.75, 0.75):
        wheel = trimesh.creation.cylinder(radius=0.42, height=0.12, sections=30)
        wheel.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [1, 0, 0]))
        wheel.apply_translation([-0.15, y, 0.42])
        wheel.visual.face_colors = tire
        parts.append(wheel)

        hub = trimesh.creation.cylinder(radius=0.12, height=0.15, sections=18)
        hub.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [1, 0, 0]))
        hub.apply_translation([-0.15, y, 0.42])
        hub.visual.face_colors = dark
        parts.append(hub)

    left_trail = trimesh.creation.box(extents=[1.55, 0.12, 0.12])
    left_trail.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(-28), [0, 0, 1]))
    left_trail.apply_translation([-1.1, 0.55, 0.22])
    left_trail.visual.face_colors = olive
    parts.append(left_trail)

    right_trail = trimesh.creation.box(extents=[1.55, 0.12, 0.12])
    right_trail.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(28), [0, 0, 1]))
    right_trail.apply_translation([-1.1, -0.55, 0.22])
    right_trail.visual.face_colors = olive
    parts.append(right_trail)

    left_spade = trimesh.creation.box(extents=[0.28, 0.26, 0.05])
    left_spade.apply_translation([-1.92, 0.95, 0.05])
    left_spade.visual.face_colors = dark
    parts.append(left_spade)

    right_spade = trimesh.creation.box(extents=[0.28, 0.26, 0.05])
    right_spade.apply_translation([-1.92, -0.95, 0.05])
    right_spade.visual.face_colors = dark
    parts.append(right_spade)

    support = trimesh.creation.box(extents=[0.4, 0.25, 0.45])
    support.apply_translation([-0.75, 0.0, 0.35])
    support.visual.face_colors = olive
    parts.append(support)

    return trimesh.util.concatenate(parts)


def normalize_howitzer_pose_glb(glb_path):
    scene = trimesh.load(glb_path, force="scene")
    mesh = scene.to_geometry()
    if hasattr(mesh, "principal_inertia_vectors"):
        forward = mesh.principal_inertia_vectors[0]
        scene.apply_transform(align_vectors(forward, [1, 0, 0]))

    extents = scene.bounds[1] - scene.bounds[0]
    rolled = False
    if extents[2] > extents[1]:
        scene.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [1, 0, 0]))
        rolled = True

    min_corner, max_corner = scene.bounds
    scene.apply_translation([
        -((min_corner[0] + max_corner[0]) / 2.0),
        -((min_corner[1] + max_corner[1]) / 2.0),
        -min_corner[2],
    ])
    with open(glb_path, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))
    extents = scene.bounds[1] - scene.bounds[0]
    print(f"[glb] normalized howitzer pose rolled={rolled} extents={extents.tolist()} -> {glb_path}")


def export_fallback_glb(output_glb):
    mesh = build_howitzer_mesh()
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
    text_prompt='M777A2 155mm howitzer, single complete towed howitzer artillery piece, connected barrel carriage wheels and trails, no soldiers, no background scene, no detached parts, clean topology, realistic military artillery gun',
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
        raise RuntimeError("Rodin job timed out for M777A2.")

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


def build_parabolic_dyn_settings():
    return {
        "freqdistPlugin": None,
        "freqdistPluginSettings": None,
        "dynSettings": {
            "projectileConfigs": {
                "gravity": 9.81,
                "muzzle_velocity": 827,
                "shell_mass": 43.1,
                "drag_coefficient": 0.295,
                "cross_section_area": 0.018,
                "max_range": 30000,
            },
            "modeSettings": [
                {"modeIndex": 0, "modeKeyword": "Launch", "modeName": "Launch", "modeNameI18n": "发射", "modeParamType": "Location"},
                {"modeIndex": 1, "modeKeyword": "SelfDestroy", "modeName": "SelfDestroy", "modeNameI18n": "自毁", "modeParamType": ""},
                {"modeIndex": 2, "modeKeyword": "Impact", "modeName": "Impact", "modeNameI18n": "打击", "modeParamType": ""},
                {"modeIndex": 30, "modeKeyword": "ChangeTargetLocation", "modeName": "ChangeTargetLocation", "modeNameI18n": "改变目标位置", "modeParamType": "Location"},
            ],
            "targetState0": {
                "target_altitude": 0,
                "target_latitude": 120.7,
                "target_longitude": 30.15,
            },
        },
        "evidences": None,
        "prejudgmentModels": None,
        "paramsfilter": None,
    }


def build_parabolic_actions():
    return [
        {
            "scriptId": f"action_{uuid.uuid4().int}",
            "axnKeyword": "Launch",
            "axnName": "发射",
            "axnNameI18n": "发射",
            "i18nLabels": [],
            "axnIcon": "",
            "vardefs": [{
                "varKeyword": "Location",
                "varName": "Location",
                "varSig": "Location",
                "varNameI18n": "Location",
                "i18nLabels": [],
                "varType": "Location",
                "stdCode": "",
                "varSchema": {},
                "varDefault": [],
                "access": 1,
                "varDecorator": "",
                "varDecoratorSettings": {},
                "varIndexCode": 0,
                "varUnit": None,
            }],
            "scriptLang": 0,
            "axnVersion": 0,
            "axnActivated": True,
            "axnRunningPlan": 0,
            "axnAsync": False,
            "axnRunningConds": ["return true;"],
            "axnScript": [
                "var num = Numbers();",
                "num.push_back(Location.lon);",
                "num.push_back(Location.lat);",
                "num.push_back(Location.hgt);",
                "Agent.dyn_set_mode(\"iagnt_dynamics_parabolic\", 0, num);",
            ],
            "axnViewDetails": [{"axnViewName": "", "axnViewKeyword": ""}],
            "scriptTalk": [],
            "actionTypeOODA": "",
            "axnDesc": "按抛物弹道发射 155mm 榴弹。",
            "access": 1,
        },
        {
            "scriptId": f"action_{uuid.uuid4().int}",
            "axnKeyword": "Impact",
            "axnName": "打击",
            "axnNameI18n": "打击",
            "i18nLabels": [],
            "axnIcon": "",
            "vardefs": [],
            "scriptLang": 0,
            "axnVersion": 0,
            "axnActivated": True,
            "axnRunningPlan": 0,
            "axnAsync": False,
            "axnRunningConds": ["return true;"],
            "axnScript": [
                "var num = Numbers();",
                "num.push_back(1.0);",
                "num.push_back(2.0);",
                "Agent.dyn_set_mode(\"iagnt_dynamics_parabolic\", 2, num);",
            ],
            "axnViewDetails": [{"axnViewName": "", "axnViewKeyword": ""}],
            "scriptTalk": [],
            "actionTypeOODA": "",
            "axnDesc": "触发落点打击逻辑。",
            "access": 0,
        },
        {
            "scriptId": f"action_{uuid.uuid4().int}",
            "axnKeyword": "SelfDestroy",
            "axnName": "自毁",
            "axnNameI18n": "自毁",
            "i18nLabels": [],
            "axnIcon": "",
            "vardefs": [],
            "scriptLang": 0,
            "axnVersion": 0,
            "axnActivated": True,
            "axnRunningPlan": 0,
            "axnAsync": False,
            "axnRunningConds": ["return true;"],
            "axnScript": [
                "var num = Numbers();",
                "num.push_back(1.0);",
                "num.push_back(2.0);",
                "Agent.dyn_set_mode(\"iagnt_dynamics_parabolic\", 1, num);",
            ],
            "axnViewDetails": [{"axnViewName": "", "axnViewKeyword": ""}],
            "scriptTalk": [],
            "actionTypeOODA": "",
            "axnDesc": "终止当前弹道并销毁弹体。",
            "access": 0,
        },
        {
            "scriptId": f"action_{uuid.uuid4().int}",
            "axnKeyword": "ChangeTargetLocation",
            "axnName": "改变目标位置",
            "axnNameI18n": "改变目标位置",
            "i18nLabels": [],
            "axnIcon": "",
            "vardefs": [{
                "varKeyword": "Location",
                "varName": "Location",
                "varSig": "Location",
                "varNameI18n": "Location",
                "i18nLabels": [],
                "varType": "Location",
                "stdCode": "",
                "varSchema": {},
                "varDefault": [],
                "access": 1,
                "varDecorator": "",
                "varDecoratorSettings": {},
                "varIndexCode": 0,
                "varUnit": None,
            }],
            "scriptLang": 0,
            "axnVersion": 0,
            "axnActivated": True,
            "axnRunningPlan": 0,
            "axnAsync": False,
            "axnRunningConds": ["return true;"],
            "axnScript": [
                "var num = Numbers();",
                "num.push_back(Location.lon);",
                "num.push_back(Location.lat);",
                "num.push_back(Location.hgt);",
                "Agent.dyn_set_mode(\"iagnt_dynamics_parabolic\", 30, num);",
            ],
            "axnViewDetails": [{"axnViewName": "", "axnViewKeyword": ""}],
            "scriptTalk": [],
            "actionTypeOODA": "",
            "axnDesc": "更新射击目标位置。",
            "access": 0,
        },
        {
            "scriptId": f"action_{uuid.uuid4().int}",
            "axnKeyword": "EnergyConsume",
            "axnName": "能量消耗",
            "axnNameI18n": "能量消耗",
            "i18nLabels": [],
            "axnIcon": "",
            "vardefs": [],
            "scriptLang": 0,
            "axnVersion": 0,
            "axnActivated": False,
            "axnRunningPlan": 0,
            "axnAsync": False,
            "axnRunningConds": ["return true;"],
            "axnScript": [
                "var energy = Agent.variables[\"energy\"].get();",
                "var energy_cost = Agent.variables[\"energyCost\"].get();",
                "var _energy = energy + energy_cost;",
                "if(_energy < 0){ _energy = 0; }",
                "if(_energy > 100){ _energy = 100; }",
                "Agent.variables[\"energy\"].set(_energy);",
            ],
            "axnViewDetails": [{"axnViewName": "", "axnViewKeyword": ""}],
            "scriptTalk": [],
            "actionTypeOODA": "",
            "axnDesc": "计算火炮射击后的资源消耗。",
            "access": 0,
        },
        {
            "scriptId": f"action_{uuid.uuid4().int}",
            "axnKeyword": "SetEnergyCost",
            "axnName": "设置能量消耗",
            "axnNameI18n": "设置能量消耗",
            "i18nLabels": [],
            "axnIcon": "",
            "vardefs": [{
                "varKeyword": "cost",
                "varName": "cost",
                "varSig": "cost",
                "varNameI18n": "cost",
                "i18nLabels": [],
                "varType": "Number",
                "stdCode": "",
                "varSchema": {},
                "varDefault": [],
                "access": 1,
                "varDecorator": "",
                "varDecoratorSettings": {},
                "varIndexCode": 0,
                "varUnit": None,
            }],
            "scriptLang": 0,
            "axnVersion": 0,
            "axnActivated": True,
            "axnRunningPlan": 0,
            "axnAsync": False,
            "axnRunningConds": ["return true;"],
            "axnScript": ["Agent.variables[\"energyCost\"].set(cost);"],
            "axnViewDetails": [{"axnViewName": "", "axnViewKeyword": ""}],
            "scriptTalk": [],
            "actionTypeOODA": "",
            "axnDesc": "调整发射后的资源消耗参数。",
            "access": 0,
        },
    ]


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
    agent["agentKeyword"] = "m777a2_howitzer"
    agent["agentUsage"] = "加载 M777A2 榴弹炮实体后，通过抛物弹道动力学执行目标点发射与打击仿真。"

    rel_png = f"{MODEL_NAME}/{PNG_FILENAME}"
    rel_mil = f"{MODEL_NAME}/{MIL_FILENAME}"
    rel_glb = f"{MODEL_NAME}/{GLB_FILENAME}"

    agent["modelUrlSlim"] = rel_glb
    agent["modelUrlFat"] = rel_glb
    agent["modelUrlSymbols"] = [
        {"symbolSeries": 1, "symbolName": rel_png, "thumbnail": rel_png},
        {"symbolSeries": 2, "symbolName": rel_mil, "thumbnail": rel_mil},
    ]

    if agent.get("missionableDynamics"):
        dyn = agent["missionableDynamics"][0]
        dyn["dynPluginName"] = "iagnt_dynamics_parabolic"
        dyn["dynKeyword"] = "iagnt_dynamics_parabolic"
        dyn.setdefault("dynSettings", {})
        dyn["dynSettings"]["pluginName"] = "iagnt_dynamics_parabolic"
        dyn["dynSettings"]["pluginNote"] = "Parabolic"
        dyn["dynSettings"]["pluginNoteI18n"] = "抛物弹道"
        dyn["dynSettings"]["pluginSignature"] = "dynamics_iagnt_dynamics_parabolic"
        dyn["dynSettings"]["pluginDefaultSettings"] = json.dumps(build_parabolic_dyn_settings(), ensure_ascii=False)

    agent["axns"] = build_parabolic_actions()

    if "model" in agent:
        agent["model"]["modelName"] = MODEL_NAME
        agent["model"]["introduction"] = AGENT_DESC
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
        print(f"[glb] BlenderMCP unavailable or howitzer generation failed, using fallback mesh: {exc}")
        export_fallback_glb(glb_path)

    normalize_howitzer_pose_glb(glb_path)
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
    print("[done] M777A2 package generated successfully.")


if __name__ == "__main__":
    main()
