from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Tuple


class ScenarioIOService:
    """Load and persist scenario artifacts from zip/json/directory inputs."""

    @staticmethod
    def load_scenario(input_path: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
        path = Path(input_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")

        if path.is_file() and path.suffix.lower() == ".zip":
            data = ScenarioIOService._load_from_zip(path)
            return data, {
                "source_type": "zip",
                "source_path": str(path),
                "source_zip_path": str(path),
            }

        if path.is_file() and path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return ScenarioIOService._normalize_root(data), {
                "source_type": "json",
                "source_path": str(path),
            }

        if path.is_dir():
            sim_json = ScenarioIOService._find_simulation_json(path)
            data = json.loads(sim_json.read_text(encoding="utf-8"))
            return ScenarioIOService._normalize_root(data), {
                "source_type": "directory",
                "source_path": str(sim_json),
            }

        raise ValueError(f"Unsupported input path: {path}")

    @staticmethod
    def dump_json(payload: Dict[str, Any], output_path: str) -> str:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return str(path)

    @staticmethod
    def _load_from_zip(zip_path: Path) -> Dict[str, Any]:
        with zipfile.ZipFile(zip_path, "r") as archive:
            simulation_member = ScenarioIOService._find_simulation_member(archive)
            with archive.open(simulation_member, "r") as fp:
                data = json.loads(fp.read().decode("utf-8"))
        return ScenarioIOService._normalize_root(data)

    @staticmethod
    def _find_simulation_member(archive: zipfile.ZipFile) -> str:
        candidates = [name for name in archive.namelist() if name.endswith("simulation.json")]
        if not candidates:
            candidates = [name for name in archive.namelist() if name.endswith(".json")]
        if not candidates:
            raise FileNotFoundError("No JSON file found in zip archive")

        # Prefer root-level simulation.json if present, otherwise shortest path.
        candidates.sort(key=lambda x: (0 if x == "simulation.json" else 1, len(x)))
        return candidates[0]

    @staticmethod
    def _find_simulation_json(directory: Path) -> Path:
        direct = directory / "simulation.json"
        if direct.exists():
            return direct
        candidates = sorted(directory.rglob("*.json"), key=lambda p: len(str(p)))
        if not candidates:
            raise FileNotFoundError(f"No JSON file found under directory: {directory}")
        return candidates[0]

    @staticmethod
    def _normalize_root(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, list):
            if not raw:
                raise ValueError("JSON root list is empty")
            if not isinstance(raw[0], dict):
                raise ValueError("JSON root list first element must be an object")
            return raw[0]
        raise ValueError(f"Unexpected JSON root type: {type(raw)}")

