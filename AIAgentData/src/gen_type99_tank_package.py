import copy
import json
import os
import re
import uuid
import zipfile
from io import BytesIO

import military_symbol
import numpy as np
import requests
import trimesh
from PIL import Image
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

from runtime_config import apply_proxy_env, get_models_dir
from validate_all import validate_files


MODEL_NAME = "Type99_Main_Battle_Tank"
MODEL_NAME_I18N = "99式主战坦克"
IMAGE_QUERY = "Type 99 main battle tank side view 3d render"
TEMPLATE_JSON = "01vehicleAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "99式主战坦克，具备地面突击与装甲对抗能力，可执行复杂陆战任务仿真。"
SYMBOL_FALLBACK_MODEL = "Dongfeng_Mengshi_CSK181"


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
    html = resp.text
    murls = re.findall(r'"murl":"(.*?)"', html) or re.findall(r"murl&quot;:&quot;(.*?)&quot;", html)

    candidates = []
    for raw in murls:
        url = raw.encode("utf-8").decode("unicode_escape").replace("\\/", "/")
        if url not in candidates:
            candidates.append(url)

    if not candidates:
        raise RuntimeError("No image candidates found for Type 99 tank.")

    good_kw = ("type-99", "type99", "99a", "main-battle-tank", "tank", "mbt")
    bad_kw = ("tire", "tyre", "wheel", "rim", "truck-tire", "alloy")
    best = None
    for url in candidates[:90]:
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
            ratio = w / max(h, 1)
            ratio_score = 100000 if 1.1 <= ratio <= 2.3 else 0
            kw_score = 200000 if any(k in lower for k in good_kw) else 0
            score = (w * h) + ratio_score + kw_score
            if best is None or score > best[0]:
                best = (score, img, url, w, h)
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Failed to download a valid Type 99 tank thumbnail.")

    _, img, src, w, h = best
    img.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {src}")


def generate_military_symbol(output_png):
    desc = "Friendly Armoured Fighting Vehicle"
    svg = military_symbol.get_symbol_svg_string_from_name(desc, style="light", bounding_padding=4, use_variants=True)
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Friendly Ground Vehicle", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        raise RuntimeError("Failed to generate military symbol.")

    tmp_svg = output_png.replace(".png", ".svg")
    with open(tmp_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    try:
        drawing = svg2rlg(tmp_svg)
        renderPM.drawToFile(drawing, output_png, fmt="PNG")
        os.remove(tmp_svg)
        print(f"[symbol] saved {output_png}")
    except Exception as exc:
        try:
            os.remove(tmp_svg)
        except OSError:
            pass
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        fallback = os.path.join(
            base,
            "models",
            SYMBOL_FALLBACK_MODEL,
            SYMBOL_FALLBACK_MODEL,
            f"{SYMBOL_FALLBACK_MODEL}_mil.png",
        )
        if not os.path.exists(fallback):
            raise RuntimeError(f"Symbol render failed and fallback missing: {exc}") from exc
        Image.open(fallback).convert("RGBA").save(output_png, "PNG")
        print(f"[symbol] fallback used from {fallback}")


def build_tank_mesh():
    parts = []
    green = [85, 102, 72, 255]
    dark = [45, 52, 41, 255]

    # Hull
    hull = trimesh.creation.box(extents=[3.3, 1.9, 0.65])
    hull.apply_translation([0, 0, 0.45])
    hull.visual.face_colors = green
    parts.append(hull)

    # Sloped front armor
    glacis = trimesh.creation.box(extents=[0.9, 1.9, 0.35])
    glacis.apply_transform(trimesh.transformations.rotation_matrix(np.radians(22), [0, 1, 0]))
    glacis.apply_translation([1.85, 0, 0.55])
    glacis.visual.face_colors = green
    parts.append(glacis)

    # Turret
    turret = trimesh.creation.cylinder(radius=0.72, height=0.42, sections=36)
    turret.apply_translation([-0.1, 0, 0.95])
    turret.visual.face_colors = green
    parts.append(turret)

    turret_top = trimesh.creation.box(extents=[1.1, 0.9, 0.24])
    turret_top.apply_translation([-0.05, 0, 1.15])
    turret_top.visual.face_colors = green
    parts.append(turret_top)

    # Cannon
    cannon = trimesh.creation.cylinder(radius=0.07, height=2.9, sections=28)
    cannon.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
    cannon.apply_translation([1.45, 0.0, 1.02])
    cannon.visual.face_colors = dark
    parts.append(cannon)

    # Tracks
    for side in (-1, 1):
        track = trimesh.creation.box(extents=[3.1, 0.32, 0.55])
        track.apply_translation([0.0, side * 1.0, 0.28])
        track.visual.face_colors = dark
        parts.append(track)
        # Road wheels hints
        for x in (-1.2, -0.7, -0.2, 0.3, 0.8, 1.3):
            wheel = trimesh.creation.cylinder(radius=0.17, height=0.1, sections=20)
            wheel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0]))
            wheel.apply_translation([x, side * 0.97, 0.19])
            wheel.visual.face_colors = [30, 30, 30, 255]
            parts.append(wheel)

    return trimesh.util.concatenate(parts)


def apply_orientation_fix(scene):
    # Strict order from skill.md
    rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
    scene.apply_transform(rot_x)
    rot_y = trimesh.transformations.rotation_matrix(np.radians(180), [0, 1, 0])
    scene.apply_transform(rot_y)


def generate_glb(output_glb):
    mesh = build_tank_mesh()
    scene = trimesh.Scene(mesh)
    apply_orientation_fix(scene)
    glb = trimesh.exchange.gltf.export_glb(scene)
    with open(output_glb, "wb") as f:
        f.write(glb)
    print(f"[glb] saved {output_glb}")


def generate_agent_json(output_json):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_path = os.path.join(base_dir, "examples", TEMPLATE_JSON)
    with open(template_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Keep vehicle dynamics + action instructions from vehicle example.
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
    generate_glb(glb_path)
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
    print("[done] Type 99 tank package generated successfully.")


if __name__ == "__main__":
    main()
