from __future__ import annotations

from pathlib import Path

from subagents.base import BaseSubAgent
from subagents.services.io_service import ScenarioIOService
from subagents.state import SubAgentState


class OperatorSubAgent(BaseSubAgent):
    """Prepare runnable artifacts for downstream execution engines."""

    def run(self, state: SubAgentState) -> SubAgentState:
        scenario_data = state.get("scenario_data", {})
        audit_report = state.get("audit_report_after_fix") or state.get("audit_report", {})
        simulation = scenario_data.get("simulation", {})
        output_dir = Path(state.get("output_dir", "outputs")).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        scenario_out = ScenarioIOService.dump_json(
            scenario_data,
            str(output_dir / "scenario.generated.json"),
        )
        audit_out = ScenarioIOService.dump_json(
            audit_report,
            str(output_dir / "audit.report.json"),
        )
        state.setdefault("artifacts", {})["scenario"] = scenario_out
        state["artifacts"]["audit_report"] = audit_out

        state["execution_plan"] = {
            "ready": True,
            "target": "LaViC MCP Bridge",
            "scenario_name": simulation.get("simulationName", "Unnamed"),
            "scenario_path": scenario_out,
            "audit_report_path": audit_out,
        }
        self.log(state, "execution artifacts generated")
        return state
