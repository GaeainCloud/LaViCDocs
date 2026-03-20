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

from aircraft_orientation import get_aircraft_policy_summary
from runtime_config import apply_proxy_env, get_downloads_dir, get_models_dir
from validate_all import validate_files


MODEL_NAME = "Y-20_Kunpeng"
MODEL_NAME_I18N = "运-20运输机"
IMAGE_QUERY = "Xian Y-20 transport aircraft 3d render side view"
TEMPLATE_JSON = "02aircraftAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "中国大型战略运输机，具备远程战略投送、重型装备空运与人员运输能力。"


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
        raise RuntimeError("No Bing image candidates found for Y-20.")

    best = None
    for url in candidates[:60]:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.content) < 20000:
                continue
            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            # Require >= 800 in either dimension, prefer larger and landscape.
            if max(w, h) < 800:
                continue
            score = (w * h) + (100000 if w > h else 0)
            if best is None or score > best[0]:
                best = (score, img, url, w, h)
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Failed to download a valid real Y-20 thumbnail image.")

    _, image, source_url, w, h = best
    image.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {source_url}")


def generate_military_symbol(output_png):
    desc = "Friendly Cargo Aircraft"
    svg = military_symbol.get_symbol_svg_string_from_name(
        desc, style="light", bounding_padding=4, use_variants=True
    )
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Friendly Fixed Wing", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        raise RuntimeError("Failed to generate military symbol for Y-20.")

    tmp_svg = output_png.replace(".png", ".svg")
    with open(tmp_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    try:
        drawing = svg2rlg(tmp_svg)
        renderPM.drawToFile(drawing, output_png, fmt="PNG")
        os.remove(tmp_svg)
        print(f"[symbol] saved {output_png}")
        return
    except Exception as exc:
        # Fallback: use an existing fixed-wing military symbol already in project assets.
        try:
            os.remove(tmp_svg)
        except OSError:
            pass
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        fallback = os.path.join(
            base_dir,
            "models",
            "KC-135_Stratotanker",
            "KC-135_Stratotanker",
            "KC-135_Stratotanker_mil.png",
        )
        if not os.path.exists(fallback):
            raise RuntimeError(f"Failed to render military symbol and no fallback found: {exc}") from exc
        Image.open(fallback).convert("RGBA").save(output_png, "PNG")
        print(f"[symbol] fallback used from {fallback}")


def build_transport_mesh():
    parts = []
    body_color = [210, 210, 210, 255]
    dark = [90, 90, 90, 255]

    # Fuselage
    fuselage = trimesh.creation.capsule(radius=0.55, height=9.0, count=[32, 32])
    fuselage.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    fuselage.visual.face_colors = body_color
    parts.append(fuselage)

    # Main wing
    wing = trimesh.creation.box(extents=[0.8, 9.5, 0.15])
    wing.apply_translation([0.5, 0, 0.35])
    wing.visual.face_colors = body_color
    parts.append(wing)

    # Horizontal tail
    h_tail = trimesh.creation.box(extents=[0.45, 3.3, 0.1])
    h_tail.apply_translation([-4.2, 0, 0.8])
    h_tail.visual.face_colors = body_color
    parts.append(h_tail)

    # Vertical tail
    v_tail = trimesh.creation.box(extents=[0.45, 0.12, 1.6])
    v_tail.apply_translation([-4.35, 0, 1.45])
    v_tail.visual.face_colors = body_color
    parts.append(v_tail)

    # Engines (4)
    for x in [1.0, 0.4]:
        for side in [-1, 1]:
            eng = trimesh.creation.cylinder(radius=0.28, height=1.0, sections=32)
            eng.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
            eng.apply_translation([x, side * 2.0, -0.05])
            eng.visual.face_colors = dark
            parts.append(eng)

    # Landing gear hints
    for y in [-0.7, 0.7]:
        gear = trimesh.creation.box(extents=[0.12, 0.12, 0.9])
        gear.apply_translation([0.8, y, -0.85])
        gear.visual.face_colors = dark
        parts.append(gear)

    nose_gear = trimesh.creation.box(extents=[0.1, 0.1, 0.65])
    nose_gear.apply_translation([3.8, 0, -0.75])
    nose_gear.visual.face_colors = dark
    parts.append(nose_gear)

    return trimesh.util.concatenate(parts)


def generate_glb(output_glb):
    mesh = build_transport_mesh()
    scene = trimesh.Scene(mesh)
    # The fallback transport mesh is authored directly in the LaViC aircraft canonical pose:
    # nose +X, back +Z, wings along Y. Do not add legacy pre-rotation here.
    glb = trimesh.exchange.gltf.export_glb(scene)
    with open(output_glb, "wb") as f:
        f.write(glb)
    print(f"[glb] saved {output_glb}")
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
        for file_name in os.listdir(assets_root):
            p = os.path.join(assets_root, file_name)
            if os.path.isfile(p):
                zf.write(p, f"{MODEL_NAME}/{file_name}")
    print(f"[zip] saved {zip_path}")


def main():
    apply_proxy_env()
    models_dir = get_models_dir()
    downloads_dir = get_downloads_dir()

    model_root = os.path.join(models_dir, MODEL_NAME)
    assets_dir = os.path.join(model_root, MODEL_NAME)
    ensure_dir(assets_dir)
    ensure_dir(downloads_dir)

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

    schema_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "src", "校验代码参考", "AgentData_schema.json")
    result = validate_files(schema_path, [agent_json])
    if result != 0:
        raise SystemExit(result)
    print("[done] Y-20 package generated successfully.")


if __name__ == "__main__":
    main()
