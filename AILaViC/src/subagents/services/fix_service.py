from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple


class FixService:
    """Apply conservative auto-fixes from audit issues."""

    @staticmethod
    def apply_safe_fixes(
        scenario_data: Dict[str, Any],
        issues: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], List[str]]:
        data = deepcopy(scenario_data)
        actions: List[str] = []

        simulation = data.setdefault("simulation", {})
        if not isinstance(simulation, dict):
            simulation = {}
            data["simulation"] = simulation
            actions.append("reset invalid simulation object")

        if not simulation.get("simulationName"):
            simulation["simulationName"] = "AI生成想定-未命名"
            actions.append("set missing simulationName")

        if not simulation.get("simulationStatus"):
            simulation["simulationStatus"] = "DRAFT"
            actions.append("set missing simulationStatus")

        if "agentInstances" not in data or not isinstance(data.get("agentInstances"), list):
            data["agentInstances"] = []
            actions.append("set agentInstances to empty list")

        # Soft normalization: ensure each agent has core keys used by probes.
        for idx, agent in enumerate(data.get("agentInstances", [])):
            if not isinstance(agent, dict):
                data["agentInstances"][idx] = {}
                agent = data["agentInstances"][idx]
                actions.append(f"normalize non-object agent entry at index {idx}")
            agent.setdefault("instanceName", f"agent-{idx}")
            agent.setdefault("agentType", "unknown")
            agent.setdefault("waypoints", [])
            agent.setdefault("axns", [])

        # Record if any hard errors appeared.
        if any((issue.get("severity") or "").upper() in {"ERROR", "CRITICAL", "FAIL"} for issue in issues):
            data.setdefault("meta", {})
            if isinstance(data["meta"], dict):
                data["meta"]["auto_fixed"] = True
                data["meta"]["fix_actions"] = actions

        return data, actions

