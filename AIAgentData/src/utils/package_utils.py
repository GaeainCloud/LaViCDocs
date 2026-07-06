"""
JSON 路径修复 / ZIP 打包 / 验收检查 共享模块
合并 fix_and_zip_models.py、zip_models.py、deep_check_paths.py 的逻辑。
"""
import json
import os
import zipfile
from pathlib import Path
from typing import List, Tuple

from logger import get_logger
from config import SCHEMA_PATH, DEFAULT_GLB_SUFFIX, DEFAULT_MIL_SUFFIX, GLB_ROTATION_MARKER

log = get_logger(__name__)

# [P1-6] 打包时需排除的内部标记文件后缀
_EXCLUDED_SUFFIXES = (GLB_ROTATION_MARKER,)


def fix_agent_json_paths(json_path: Path, model_name: str) -> bool:
    """修复 agent.json 中的所有资源路径引用。

    更新以下字段：
    - 根级: agentName, modelUrlSlim, modelUrlFat, modelUrlSymbols
    - model 对象: modelName, thumbnail, mapIconUrl, dimModelUrls

    Args:
        json_path: agent.json 文件路径
        model_name: 模型名称（用于构建路径）

    Returns:
        True 表示有更新
    """
    json_path = Path(json_path)
    if not json_path.exists():
        log.warning(f"文件不存在: {json_path}")
        return False

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        log.error(f"JSON 读取失败 ({json_path}): {e}")
        return False

    def _update_agent(agent: dict, name: str) -> bool:
        updated = False
        glb_filename = f"{name}{DEFAULT_GLB_SUFFIX}"
        png_filename = f"{name}.png"
        mil_filename = f"{name}{DEFAULT_MIL_SUFFIX}"
        glb_path = f"{name}/{glb_filename}"
        png_path = f"{name}/{png_filename}"
        mil_path = f"{name}/{mil_filename}"

        # model 对象
        if "model" in agent:
            agent["model"]["modelName"] = name

            if "thumbnail" in agent["model"]:
                agent["model"]["thumbnail"]["url"] = png_path
                agent["model"]["thumbnail"]["ossSig"] = png_filename

            if "mapIconUrl" in agent["model"]:
                agent["model"]["mapIconUrl"]["url"] = mil_path
                agent["model"]["mapIconUrl"]["ossSig"] = mil_filename

            if "dimModelUrls" in agent["model"] and isinstance(agent["model"]["dimModelUrls"], list):
                for dim_model in agent["model"]["dimModelUrls"]:
                    dim_model["url"] = glb_path
                    dim_model["ossSig"] = glb_filename

            updated = True

        # 根级 GLB 路径
        if "modelUrlSlim" in agent:
            agent["modelUrlSlim"] = glb_path
            updated = True
        if "modelUrlFat" in agent:
            agent["modelUrlFat"] = glb_path
            updated = True

        # 根级 Symbols
        if "modelUrlSymbols" in agent and isinstance(agent["modelUrlSymbols"], list):
            for symbol in agent["modelUrlSymbols"]:
                if symbol.get("symbolSeries") == 1:
                    symbol["symbolName"] = png_path
                    symbol["thumbnail"] = png_path
                    updated = True
                elif symbol.get("symbolSeries") == 2:
                    symbol["symbolName"] = mil_path
                    symbol["thumbnail"] = mil_path
                    updated = True

        return updated

    updated = False
    if isinstance(data, list):
        for item in data:
            if _update_agent(item, model_name):
                updated = True
    elif isinstance(data, dict):
        updated = _update_agent(data, model_name)

    if updated:
        log.info(f"更新路径: {model_name}")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return updated


def _is_excluded_file(filename: str) -> bool:
    """判断文件是否应被排除在 ZIP 包之外。"""
    return any(filename.endswith(suffix) for suffix in _EXCLUDED_SUFFIXES)


def create_flat_zip(model_dir: Path, output_path: Path):
    """创建 UTF-8 编码的扁平化 ZIP。

    ZIP 结构：
      agent.json
      {ModelName}/
        {ModelName}.png
        {ModelName}_mil.png
        {ModelName}_AI_Rodin.glb

    会自动排除 .rotation_applied 等内部标记文件。

    Args:
        model_dir: 模型目录（包含 agent.json 和子文件夹）
        output_path: 输出 ZIP 文件路径
    """
    model_dir = Path(model_dir)
    output_path = Path(output_path)

    if not model_dir.exists():
        log.error(f"模型目录不存在: {model_dir}")
        return

    log.info(f"打包: {model_dir.name} -> {output_path.name}")

    try:
        with zipfile.ZipFile(str(output_path), "w", zipfile.ZIP_DEFLATED) as zipf:
            # [P0-1] 使用 os.walk() 替代 Path.walk()，兼容 Python < 3.12
            for root, _, files in os.walk(str(model_dir)):
                for file in files:
                    # [P1-6] 排除幂等性标记文件
                    if _is_excluded_file(file):
                        continue
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(model_dir)
                    zipf.write(str(file_path), arcname=str(rel_path))

        log.info(f"打包完成: {output_path}")

    except Exception as e:
        log.error(f"打包失败 ({model_dir.name}): {e}")


def validate_package(zip_path: Path) -> Tuple[bool, List[str]]:
    """验收检查：解压验证文件完整性和路径一致性。

    检查项：
    1. agent.json 是否存在
    2. agent.json 中引用的路径是否在 ZIP 内存在
    3. Schema 校验（如果 schema 文件存在）— Schema 问题归为 warnings

    Args:
        zip_path: ZIP 文件路径

    Returns:
        (通过/失败, 错误消息列表)
        注意: Schema 校验问题不影响通过/失败判定（仅作为警告输出）
    """
    zip_path = Path(zip_path)
    errors: List[str] = []
    warnings: List[str] = []

    if not zip_path.exists():
        return False, [f"文件不存在: {zip_path}"]

    try:
        with zipfile.ZipFile(str(zip_path), "r") as z:
            file_list = z.namelist()

            # 1. agent.json
            if "agent.json" not in file_list:
                errors.append("agent.json 缺失")
                return False, errors

            # 2. 读取 agent.json
            json_content = z.read("agent.json").decode("utf-8")
            data = json.loads(json_content)

            agent = data[0] if isinstance(data, list) else data

            # 3. 检查路径引用
            path_fields = ["modelUrlSlim", "modelUrlFat", "modelUrlMedium", "modelUrlPAK"]
            for field in path_fields:
                val = agent.get(field)
                if val and val not in file_list:
                    errors.append(f"字段 '{field}' 引用的文件不在 ZIP 中: {val}")

            # 4. 检查 symbols
            symbols = agent.get("modelUrlSymbols", [])
            for idx, sym in enumerate(symbols):
                for key in ["symbolName", "thumbnail"]:
                    val = sym.get(key)
                    if val and not val.startswith("http") and val not in file_list:
                        errors.append(f"modelUrlSymbols[{idx}].{key} 引用的文件不在 ZIP 中: {val}")

            # 5. 检查 model 对象内的路径
            model = agent.get("model", {})
            if model:
                thumb = model.get("thumbnail", {})
                if isinstance(thumb, dict):
                    thumb_url = thumb.get("url", "")
                    if thumb_url and not thumb_url.startswith("http") and thumb_url not in file_list:
                        errors.append(f"model.thumbnail.url 引用的文件不在 ZIP 中: {thumb_url}")

                map_icon = model.get("mapIconUrl", {})
                if isinstance(map_icon, dict):
                    icon_url = map_icon.get("url", "")
                    if icon_url and not icon_url.startswith("http") and icon_url not in file_list:
                        errors.append(f"model.mapIconUrl.url 引用的文件不在 ZIP 中: {icon_url}")

                dim_models = model.get("dimModelUrls", [])
                for i, dm in enumerate(dim_models):
                    dm_url = dm.get("url", "")
                    if dm_url and not dm_url.startswith("http") and dm_url not in file_list:
                        errors.append(f"model.dimModelUrls[{i}].url 引用的文件不在 ZIP 中: {dm_url}")

            # 6. [P2-5] Schema 校验结果归为 warnings，不影响通过判定
            if SCHEMA_PATH.exists():
                try:
                    from jsonschema import Draft7Validator

                    with open(SCHEMA_PATH, "r", encoding="utf-8") as sf:
                        schema = json.load(sf)

                    validator = Draft7Validator(schema)
                    schema_errors = list(validator.iter_errors(data))
                    for err in schema_errors[:5]:
                        path_str = "/".join(map(str, err.path)) if err.path else "(root)"
                        warnings.append(f"Schema 警告: [{path_str}] {err.message}")
                except ImportError:
                    warnings.append("jsonschema 未安装，跳过 Schema 校验")

    except Exception as e:
        return False, [f"验收检查异常: {e}"]

    passed = len(errors) == 0
    if passed:
        log.info(f"验收通过: {zip_path.name}")
    else:
        log.warning(f"验收发现 {len(errors)} 个错误: {zip_path.name}")
        for err in errors:
            log.warning(f"  - {err}")

    if warnings:
        log.info(f"验收警告 ({len(warnings)} 条):")
        for w in warnings:
            log.info(f"  - {w}")

    return passed, errors
