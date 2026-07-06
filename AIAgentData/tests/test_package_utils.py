import json
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import utils.package_utils as package_utils


def test_fix_agent_json_paths_updates_nested_and_root(tmp_path):
    model_name = "Test_Model"
    agent = [{
        "agentName": "old",
        "modelUrlSlim": "old.glb",
        "modelUrlFat": "old.glb",
        "modelUrlSymbols": [
            {"symbolSeries": 1, "symbolName": "old.png", "thumbnail": "old.png"},
            {"symbolSeries": 2, "symbolName": "old_mil.png", "thumbnail": "old_mil.png"},
        ],
        "model": {
            "modelName": "old",
            "thumbnail": {"url": "old.png", "ossSig": "old.png"},
            "mapIconUrl": {"url": "old_mil.png", "ossSig": "old_mil.png"},
            "dimModelUrls": [{"url": "old.glb", "ossSig": "old.glb"}],
        },
    }]
    json_path = tmp_path / "agent.json"
    json_path.write_text(json.dumps(agent, ensure_ascii=False), encoding="utf-8")

    changed = package_utils.fix_agent_json_paths(json_path, model_name)
    assert changed

    data = json.loads(json_path.read_text(encoding="utf-8"))
    a = data[0]
    assert a["modelUrlSlim"] == f"{model_name}/{model_name}_AI_Rodin.glb"
    assert a["model"]["thumbnail"]["url"] == f"{model_name}/{model_name}.png"
    assert a["model"]["mapIconUrl"]["url"] == f"{model_name}/{model_name}_mil.png"


def test_validate_package_checks_zip_paths_without_schema(tmp_path, monkeypatch):
    # 避免依赖完整 schema，专注验证路径一致性
    monkeypatch.setattr(package_utils, "SCHEMA_PATH", tmp_path / "missing_schema.json")

    model_name = "PkgModel"
    agent = [{
        "modelUrlSlim": f"{model_name}/{model_name}_AI_Rodin.glb",
        "modelUrlFat": f"{model_name}/{model_name}_AI_Rodin.glb",
        "modelUrlSymbols": [
            {"symbolSeries": 1, "symbolName": f"{model_name}/{model_name}.png", "thumbnail": f"{model_name}/{model_name}.png"},
            {"symbolSeries": 2, "symbolName": f"{model_name}/{model_name}_mil.png", "thumbnail": f"{model_name}/{model_name}_mil.png"},
        ],
        "model": {
            "thumbnail": {"url": f"{model_name}/{model_name}.png"},
            "mapIconUrl": {"url": f"{model_name}/{model_name}_mil.png"},
            "dimModelUrls": [{"url": f"{model_name}/{model_name}_AI_Rodin.glb"}],
        },
    }]

    zip_path = tmp_path / "PkgModel.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("agent.json", json.dumps(agent, ensure_ascii=False))
        zf.writestr(f"{model_name}/{model_name}.png", b"png")
        zf.writestr(f"{model_name}/{model_name}_mil.png", b"png")
        zf.writestr(f"{model_name}/{model_name}_AI_Rodin.glb", b"glb")

    passed, errors = package_utils.validate_package(zip_path)
    assert passed is True
    assert errors == []
