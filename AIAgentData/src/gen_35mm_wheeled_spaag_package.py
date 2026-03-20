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


MODEL_NAME = "35mm_Wheeled_SPAAG"
MODEL_NAME_I18N = "35毫米轮式自行高炮"
IMAGE_QUERY = "35mm wheeled self-propelled anti-aircraft gun side view"
TEMPLATE_JSON = "01vehicleAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "35毫米轮式自行高炮，具备机动伴随防空与近程对空火力拦截能力。"
PREFERRED_IMAGE_URLS = [
    "https://preview.redd.it/chinese-cs-sa1-35mm-self-propelled-anti-aircraft-gun-v0-kntypkjqg15c1.jpg?width=1080&crop=smart&auto=webp&s=17d2a8e2d2cf6ac37041f30da474f6bc45db13a1",
    "https://www.globalsecurity.org/military/world/china/images/sws2-image09.jpg",
    "https://www.globalsecurity.org/military/world/china/images/sws2-image03.jpg",
]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def fetch_real_thumbnail(output_png: str) -> None:
    headers = {"User-Agent": "Mozilla/5.0"}
    # Prefer known wheeled 35mm SPAAG references first.
    for url in PREFERRED_IMAGE_URLS:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.content) < 30000:
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
        raise RuntimeError("No image candidates found for 35mm Wheeled SPAAG.")

    good_kw = (
        "35mm",
        "self-propelled",
        "anti-air",
        "air-defense",
        "spaag",
        "wheeled",
        "gun",
        "pgz",
        "sws2",
        "cs-sa1",
        "type 09",
    )
    bad_kw = ("logo", "icon", "patch", "wallpaper", "toy", "diagram", "blueprint", "shilka", "tracked")
    best = None

    for url in candidates[:120]:
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
            ratio_score = 120000 if 1.1 <= ratio <= 2.6 else 0
            kw_score = 230000 if any(k in lower for k in good_kw) else 0
            score = (w * h) + ratio_score + kw_score
            if best is None or score > best[0]:
                best = (score, img, url, w, h)
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Failed to download a valid thumbnail for 35mm Wheeled SPAAG.")

    _, img, src, w, h = best
    img.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {src}")


def generate_red_military_symbol(output_png: str) -> None:
    # From military symbol library (GitHub package), red side symbol.
    # Use explicit hostile air-defense gun name to avoid wrong entity mapping.
    desc = "Hostile Self-Propelled Air Defense Gun"
    svg = military_symbol.get_symbol_svg_string_from_name(desc, style="light", bounding_padding=4, use_variants=True)
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Hostile Air Defense Artillery", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        raise RuntimeError("Failed to generate hostile military symbol from library.")

    png_bytes = resvg_py.svg_to_bytes(svg)
    with open(output_png, "wb") as f:
        f.write(png_bytes)
    print(f"[symbol] saved {output_png} (hostile/red, from military_symbol library)")


def build_spaag_mesh() -> trimesh.Trimesh:
    parts = []
    hull_color = [102, 112, 100, 255]
    dark = [48, 52, 46, 255]
    tire = [22, 22, 22, 255]
    metal = [88, 92, 84, 255]

    # Chassis / hull
    hull = trimesh.creation.box(extents=[5.2, 2.3, 0.85])
    hull.apply_translation([0.0, 0.0, 0.62])
    hull.visual.face_colors = hull_color
    parts.append(hull)

    cabin = trimesh.creation.box(extents=[1.45, 2.15, 0.92])
    cabin.apply_translation([1.55, 0.0, 1.02])
    cabin.visual.face_colors = hull_color
    parts.append(cabin)

    turret_base = trimesh.creation.box(extents=[1.7, 1.9, 0.6])
    turret_base.apply_translation([-0.5, 0.0, 1.22])
    turret_base.visual.face_colors = metal
    parts.append(turret_base)

    radar = trimesh.creation.box(extents=[0.16, 1.45, 0.95])
    radar.apply_translation([-1.4, 0.0, 1.62])
    radar.visual.face_colors = dark
    parts.append(radar)

    # Twin 35mm cannons
    for y in (-0.35, 0.35):
        barrel = trimesh.creation.cylinder(radius=0.055, height=2.5, sections=22)
        barrel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
        barrel.apply_translation([0.85, y, 1.28])
        barrel.visual.face_colors = dark
        parts.append(barrel)

    # Wheels (8x8)
    wheel_x = [-1.75, -1.0, -0.25, 0.5, 1.25, 2.0, 2.75, 3.5]
    for x in wheel_x:
        for side in (-1, 1):
            wheel = trimesh.creation.cylinder(radius=0.39, height=0.32, sections=26)
            wheel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0]))
            wheel.apply_translation([x - 1.0, side * 1.12, 0.38])
            wheel.visual.face_colors = tire
            parts.append(wheel)

            hub = trimesh.creation.cylinder(radius=0.17, height=0.1, sections=20)
            hub.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0]))
            hub.apply_translation([x - 1.0, side * 1.12, 0.38])
            hub.visual.face_colors = dark
            parts.append(hub)

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
    mesh = build_spaag_mesh()
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

    # Vehicle template: keeps vehicle dynamics and action instructions.
    agent = copy.deepcopy(data[0] if isinstance(data, list) else data)
    agent["agentKey"] = f"AGENTKEY_{uuid.uuid4().int}"
    agent["agentName"] = MODEL_NAME
    agent["agentNameI18n"] = MODEL_NAME_I18N
    agent["agentDesc"] = AGENT_DESC
    agent["agentCoreFunc"] = AGENT_DESC
    agent["agentKeyword"] = "wheeled_spaag_35mm"

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
    print("[done] 35mm Wheeled SPAAG package generated successfully.")


if __name__ == "__main__":
    main()
