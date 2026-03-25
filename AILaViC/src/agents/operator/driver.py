from __future__ import annotations

from pathlib import Path


class Driver:
    """
    Backward-compatible operator wrapper.
    """

    def run_scenario(self, scenario_path: str):
        path = Path(scenario_path).expanduser().resolve()
        return {
            "accepted": path.exists(),
            "scenario_path": str(path),
            "message": "MCP bridge call is not wired yet; scenario artifact prepared.",
        }
