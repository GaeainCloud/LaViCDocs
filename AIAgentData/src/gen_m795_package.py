import copy
import json
import os
import socket
import time
import uuid
import zipfile

import military_symbol
import numpy as np
import resvg_py
import trimesh
from PIL import Image, ImageDraw, ImageFont
from trimesh.geometry import align_vectors

from runtime_config import apply_proxy_env, get_models_dir
from validate_all import validate_files

MODEL_NAME = "M795_155mm_HE_Shell"
MODEL_NAME_I18N = "M795 高爆弹"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
TEMPLATE_JSON = "08boundingMineAgent.json"
AGENT_DESC = "M795 155mm高爆炮弹模型，采用抛物弹道动力学执行火炮射击与弹道打击仿真。"


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
    img.thumbnail((1240, 760))
    canvas.paste(img, ((canvas.width - img.width) // 2, (canvas.height - img.height) // 2))
    return canvas


def fetch_real_thumbnail(output_png):
    # Use a clean synthetic shell illustration so the thumbnail stays as a
    # single, complete artillery round rather than a brochure crop.
    width, height = 1400, 900
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    draw.ellipse((230, 410, 1170, 520), fill=(235, 235, 235))
    draw.rounded_rectangle((280, 320, 1020, 420), radius=48, fill=(173, 168, 119), outline=(120, 116, 80), width=4)
    draw.polygon([(1020, 320), (1155, 370), (1020, 420)], fill=(173, 168, 119), outline=(120, 116, 80))
    draw.rounded_rectangle((225, 332, 285, 408), radius=18, fill=(96, 92, 70), outline=(70, 68, 52), width=3)
    draw.rounded_rectangle((760, 320, 825, 420), radius=8, fill=(186, 121, 58), outline=(145, 92, 45), width=3)
    draw.rounded_rectangle((1142, 354, 1184, 386), radius=12, fill=(85, 85, 85), outline=(50, 50, 50), width=2)
    for x in (350, 470, 620, 905):
        draw.line((x, 330, x, 410), fill=(135, 132, 95), width=2)

    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 44)
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 26)
        draw.text((360, 455), "M795 155mm HE", fill=(60, 60, 60), font=title_font)
        draw.text((408, 510), "High Explosive Artillery Shell", fill=(100, 100, 100), font=subtitle_font)
    except Exception:
        pass

    normalize_thumbnail(img).save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png}")
    print("[thumbnail] source synthetic single-shell illustration")



def generate_military_symbol(output_png):
    candidates = [
        "Friendly Projectile",
        "Friendly Munition",
        "Friendly Missile",
    ]
    svg = None
    for name in candidates:
        svg = military_symbol.get_symbol_svg_string_from_name(
            name, style="light", bounding_padding=4, use_variants=True
        )
        if svg:
            break
    if svg is None:
        raise RuntimeError("Failed to generate military symbol for M795 shell.")
    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png}")



def build_shell_mesh():
    olive = [164, 161, 111, 255]
    copper = [186, 116, 50, 255]
    dark = [96, 94, 72, 255]
    parts = []

    body = trimesh.creation.cylinder(radius=0.13, height=1.35, sections=48)
    body.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    body.apply_translation([0.05, 0.0, 0.13])
    body.visual.face_colors = olive
    parts.append(body)

    nose = trimesh.creation.cone(radius=0.13, height=0.45, sections=48)
    nose.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    nose.apply_translation([0.95, 0.0, 0.13])
    nose.visual.face_colors = olive
    parts.append(nose)

    tail = trimesh.creation.cylinder(radius=0.085, height=0.18, sections=40)
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    tail.apply_translation([-0.72, 0.0, 0.13])
    tail.visual.face_colors = dark
    parts.append(tail)

    band = trimesh.creation.cylinder(radius=0.1325, height=0.10, sections=48)
    band.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    band.apply_translation([0.52, 0.0, 0.13])
    band.visual.face_colors = copper
    parts.append(band)

    fuze = trimesh.creation.cylinder(radius=0.038, height=0.09, sections=24)
    fuze.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [0, 1, 0]))
    fuze.apply_translation([1.17, 0.0, 0.13])
    fuze.visual.face_colors = dark
    parts.append(fuze)

    mesh = trimesh.util.concatenate(parts)
    return mesh



def estimate_end_radius(mesh, xmin, xmax, sample_width=0.12):
    verts = mesh.vertices
    if len(verts) == 0:
        return 0.0, 0.0
    span = xmax - xmin
    low = verts[verts[:, 0] <= xmin + sample_width * span]
    high = verts[verts[:, 0] >= xmax - sample_width * span]
    low_r = float(np.mean(np.sqrt(low[:, 1] ** 2 + low[:, 2] ** 2))) if len(low) else 0.0
    high_r = float(np.mean(np.sqrt(high[:, 1] ** 2 + high[:, 2] ** 2))) if len(high) else 0.0
    return low_r, high_r



def normalize_shell_pose_glb(glb_path):
    scene = trimesh.load(glb_path, force="scene")
    mesh = scene.to_geometry()
    if hasattr(mesh, "principal_inertia_vectors"):
        forward = mesh.principal_inertia_vectors[0]
        scene.apply_transform(align_vectors(forward, [1, 0, 0]))

    mesh = scene.to_geometry()
    bounds = mesh.bounds
    extents = bounds[1] - bounds[0]
    rolled = False
    reversed_heading = False

    if extents[2] > extents[1] * 1.05:
        scene.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(90), [1, 0, 0]))
        rolled = True
        mesh = scene.to_geometry()
        bounds = mesh.bounds

    xmin, xmax = bounds[0][0], bounds[1][0]
    low_r, high_r = estimate_end_radius(mesh, xmin, xmax)
    if high_r > 0 and low_r > 0 and high_r > low_r * 1.18:
        scene.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(180), [0, 0, 1]))
        reversed_heading = True

    min_corner, max_corner = scene.bounds
    scene.apply_translation([
        -((min_corner[0] + max_corner[0]) / 2.0),
        -((min_corner[1] + max_corner[1]) / 2.0),
        -min_corner[2],
    ])
    with open(glb_path, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))
    extents = scene.bounds[1] - scene.bounds[0]
    print(f"[glb] normalized shell pose rolled={rolled} reversed={reversed_heading} extents={extents.tolist()} -> {glb_path}")



def export_fallback_glb(output_glb):
    mesh = build_shell_mesh()
    scene = trimesh.Scene(mesh)
    with open(output_glb, "wb") as f:
        f.write(trimesh.exchange.gltf.export_glb(scene))
    print(f"[glb] fallback saved {output_glb}")



def generate_glb_with_blendermcp(image_path, output_glb):
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
    text_prompt='M795 155mm high explosive artillery projectile, single complete artillery shell, clean ogive nose, cylindrical body, no launcher, no people, no background scene, no detached parts, realistic military projectile',
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
        raise RuntimeError("Rodin job timed out for M795 shell.")

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
                "shell_mass": 46.7,
                "drag_coefficient": 0.295,
                "cross_section_area": 0.018,
                "max_range": 22500,
            },
            "modeSettings": [
                {"modeIndex": 0, "modeKeyword": "Launch", "modeName": "Launch", "modeNameI18n": "发射", "modeParamType": "Location"},
                {"modeIndex": 1, "modeKeyword": "SelfDestroy", "modeName": "SelfDestroy", "modeNameI18n": "自毁", "modeParamType": ""},
                {"modeIndex": 2, "modeKeyword": "Impact", "modeName": "Impact", "modeNameI18n": "打击", "modeParamType": ""},
                {"modeIndex": 30, "modeKeyword": "ChangeTargetLocation", "modeName": "ChangeTargetLocation", "modeNameI18n": "改变目标位置", "modeParamType": "Location"},
            ],
            "targetState0": {"target_altitude": 0, "target_latitude": 30.15, "target_longitude": 120.7},
        },
        "evidences": None,
        "prejudgmentModels": None,
        "paramsfilter": None,
    }



def build_parabolic_actions():
    loc_vardef = {
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
    }
    cost_vardef = {
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
    }
    return [
        {
            "scriptId": f"action_{uuid.uuid4().int}",
            "axnKeyword": "Launch",
            "axnName": "发射",
            "axnNameI18n": "发射",
            "i18nLabels": [],
            "axnIcon": "",
            "vardefs": [loc_vardef],
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
            "axnDesc": "发射 M795 高爆弹。",
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
            "vardefs": [loc_vardef],
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
            "axnDesc": "更新打击目标位置。",
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
            "axnDesc": "计算炮弹资源消耗。",
            "access": 0,
        },
        {
            "scriptId": f"action_{uuid.uuid4().int}",
            "axnKeyword": "SetEnergyCost",
            "axnName": "设置能量消耗",
            "axnNameI18n": "设置能量消耗",
            "i18nLabels": [],
            "axnIcon": "",
            "vardefs": [cost_vardef],
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
            "axnDesc": "调整资源消耗参数。",
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
    agent["agentKeyword"] = "m795_155mm_he_shell"
    agent["agentUsage"] = "加载 M795 高爆弹实体后，通过抛物弹道动力学执行目标点打击仿真。"

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
        print(f"[glb] BlenderMCP unavailable or shell generation failed, using fallback mesh: {exc}")
        export_fallback_glb(glb_path)

    normalize_shell_pose_glb(glb_path)
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
    print("[done] M795 shell package generated successfully.")


if __name__ == "__main__":
    main()
