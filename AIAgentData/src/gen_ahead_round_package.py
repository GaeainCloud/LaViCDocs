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
import resvg_py
import trimesh
from PIL import Image

from runtime_config import apply_proxy_env, get_models_dir
from validate_all import validate_files


MODEL_NAME = "AHEAD_Fragmentation_Round"
MODEL_NAME_I18N = "AHEAD破片弹"
IMAGE_QUERY = "AHEAD 35mm programmable ammunition round render"
TEMPLATE_JSON = "08boundingMineAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "AHEAD可编程破片弹模型，用于近程防空拦截与空爆杀伤效能仿真。"
PREFERRED_IMAGE_URLS = [
    "https://euro-sd.com/wp-content/uploads/2024/05/AHEAD-ammo-Rheinmetall.jpg",
    "https://www.edrmagazine.eu/wp-content/uploads/2024/05/Rheinmetall-35-mm-AHEAD-contract.jpg",
]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def fetch_real_thumbnail(output_png: str) -> None:
    headers = {"User-Agent": "Mozilla/5.0"}

    for url in PREFERRED_IMAGE_URLS:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.content) < 20000:
                continue
            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 700:
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
    html = resp.text
    murls = re.findall(r'"murl":"(.*?)"', html) or re.findall(r"murl&quot;:&quot;(.*?)&quot;", html)

    candidates = []
    for raw in murls:
        url = raw.encode("utf-8").decode("unicode_escape").replace("\\/", "/")
        if url not in candidates:
            candidates.append(url)

    if not candidates:
        raise RuntimeError("No image candidates found for AHEAD round.")

    good_kw = (
        "ahead",
        "35mm",
        "rheinmetall",
        "ammunition",
        "round",
        "fragmentation",
        "programmable",
    )
    bad_kw = ("logo", "icon", "patch", "toy", "blueprint", "diagram", "wallpaper")
    best = None

    for url in candidates[:120]:
        lower = url.lower()
        if any(k in lower for k in bad_kw):
            continue
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.content) < 18000:
                continue
            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 700:
                continue
            ratio = w / max(h, 1)
            ratio_score = 120000 if 1.1 <= ratio <= 2.8 else 0
            kw_score = 240000 if any(k in lower for k in good_kw) else 0
            score = (w * h) + ratio_score + kw_score
            if best is None or score > best[0]:
                best = (score, img, url, w, h)
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Failed to download a valid thumbnail for AHEAD round.")

    _, img, src, w, h = best
    img.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {src}")


def generate_red_military_symbol(output_png: str) -> None:
    # Use symbol library directly; hostile (red) missile icon.
    desc = "Hostile Missile"
    sym = military_symbol.get_symbol_class_from_name(desc)
    sidc = sym.get_sidc()
    svg = military_symbol.get_symbol_svg_string_from_sidc(sidc, style="light", bounding_padding=4)
    if svg is None:
        raise RuntimeError("Failed to generate hostile symbol from military symbol library.")

    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png} (hostile/red, SIDC={sidc})")


def build_ahead_round_mesh() -> trimesh.Trimesh:
    parts = []
    body_color = [212, 192, 122, 255]
    cap_color = [228, 208, 148, 255]
    band_color = [146, 120, 62, 255]

    # Main body (cartridge-like projectile)
    body = trimesh.creation.cylinder(radius=0.11, height=0.82, sections=40)
    body.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
    body.visual.face_colors = body_color
    parts.append(body)

    # Nose cone
    nose = trimesh.creation.cone(radius=0.11, height=0.18, sections=40)
    nose.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
    nose.apply_translation([0.50, 0.0, 0.0])
    nose.visual.face_colors = cap_color
    parts.append(nose)

    # Base cap
    base = trimesh.creation.cylinder(radius=0.105, height=0.05, sections=30)
    base.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
    base.apply_translation([-0.44, 0.0, 0.0])
    base.visual.face_colors = band_color
    parts.append(base)

    # Programming band
    band = trimesh.creation.cylinder(radius=0.113, height=0.06, sections=36)
    band.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
    band.apply_translation([0.15, 0.0, 0.0])
    band.visual.face_colors = band_color
    parts.append(band)

    return trimesh.util.concatenate(parts)


def apply_orientation_fix(scene: trimesh.Scene) -> None:
    # skill.md strict order:
    # 1) X -90 (Z-up -> Y-up)
    # 2) Y 180  (facing correction)
    rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
    scene.apply_transform(rot_x)
    rot_y = trimesh.transformations.rotation_matrix(np.radians(180), [0, 1, 0])
    scene.apply_transform(rot_y)


def generate_glb(output_glb: str) -> None:
    mesh = build_ahead_round_mesh()
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

    # Use mine/bomb-like template dynamics and action instructions.
    agent = copy.deepcopy(data[0] if isinstance(data, list) else data)
    agent["agentKey"] = f"AGENTKEY_{uuid.uuid4().int}"
    agent["agentName"] = MODEL_NAME
    agent["agentNameI18n"] = MODEL_NAME_I18N
    agent["agentDesc"] = AGENT_DESC
    agent["agentCoreFunc"] = AGENT_DESC
    agent["agentKeyword"] = "ahead_fragmentation_round"

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
    generate_red_military_symbol(mil_png)
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
    print("[done] AHEAD round package generated successfully.")


if __name__ == "__main__":
    main()
