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

from runtime_config import apply_proxy_env, get_downloads_dir, get_models_dir
from validate_all import validate_files


MODEL_NAME = "Dongfang_Mengshi_Gen3"
MODEL_NAME_I18N = "东方猛士三代战车"
IMAGE_QUERY = "Dongfeng Mengshi CSK181 armored vehicle 3/4 view clean background"
TEMPLATE_JSON = "01vehicleAgent.json"
GLB_FILENAME = f"{MODEL_NAME}_AI_Rodin.glb"
PNG_FILENAME = f"{MODEL_NAME}.png"
MIL_FILENAME = f"{MODEL_NAME}_mil.png"
AGENT_DESC = "东方猛士三代战车，具备机动突击与战场运输能力，适用于地面战术任务仿真。"
SOURCE_MODEL_FALLBACK = "Dongfeng_Mengshi_CSK181"


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
        raise RuntimeError("No Bing image candidates found for Mengshi Gen3.")

    best = None
    for url in candidates[:80]:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.content) < 20000:
                continue
            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 800:
                continue
            # Prefer 3/4-ish landscape photos and larger sizes.
            ratio = w / max(h, 1)
            ratio_score = 120000 if 1.1 <= ratio <= 2.2 else 0
            score = (w * h) + ratio_score
            if best is None or score > best[0]:
                best = (score, img, url, w, h)
        except Exception:
            continue

    if best is None:
        raise RuntimeError("Failed to download a valid real thumbnail for Mengshi Gen3.")

    _, image, source_url, w, h = best
    image.save(output_png, "PNG")
    print(f"[thumbnail] saved {output_png} ({w}x{h})")
    print(f"[thumbnail] source {source_url}")


def generate_military_symbol(output_png):
    desc = "Friendly Armoured Fighting Vehicle"
    svg = military_symbol.get_symbol_svg_string_from_name(
        desc, style="light", bounding_padding=4, use_variants=True
    )
    if svg is None:
        svg = military_symbol.get_symbol_svg_string_from_name(
            "Friendly Ground Vehicle", style="light", bounding_padding=4, use_variants=True
        )
    if svg is None:
        raise RuntimeError("Failed to generate military symbol for Mengshi Gen3.")

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
        try:
            os.remove(tmp_svg)
        except OSError:
            pass
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        fallback = os.path.join(
            base_dir,
            "models",
            SOURCE_MODEL_FALLBACK,
            SOURCE_MODEL_FALLBACK,
            f"{SOURCE_MODEL_FALLBACK}_mil.png",
        )
        if not os.path.exists(fallback):
            raise RuntimeError(f"Failed to render military symbol and no fallback found: {exc}") from exc
        Image.open(fallback).convert("RGBA").save(output_png, "PNG")
        print(f"[symbol] fallback used from {fallback}")


def apply_orientation_fix(scene):
    # Strict order per skill.md:
    # 1) X -90 degrees (Z-up -> Y-up)
    # 2) Y 180 degrees (facing correction)
    rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
    scene.apply_transform(rot_x)
    rot_y = trimesh.transformations.rotation_matrix(np.radians(180), [0, 1, 0])
    scene.apply_transform(rot_y)


def generate_glb(output_glb):
    downloads_dir = get_downloads_dir()
    src = os.path.join(downloads_dir, f"{SOURCE_MODEL_FALLBACK}_AI_Rodin.glb")
    if not os.path.exists(src):
        raise RuntimeError(f"Source GLB not found: {src}")
    scene = trimesh.load(src, force="scene")
    apply_orientation_fix(scene)
    glb = trimesh.exchange.gltf.export_glb(scene)
    with open(output_glb, "wb") as f:
        f.write(glb)
    print(f"[glb] saved {output_glb} from {src}")


def generate_agent_json(output_json):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_path = os.path.join(base_dir, "examples", TEMPLATE_JSON)
    with open(template_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Keep vehicle dynamics + actions/ooda structure from example.
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

    schema_path = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        "src",
        "校验代码参考",
        "AgentData_schema.json",
    )
    result = validate_files(schema_path, [agent_json])
    if result != 0:
        raise SystemExit(result)
    print("[done] Mengshi Gen3 package generated successfully.")


if __name__ == "__main__":
    main()
