from __future__ import annotations

from subagents.base import BaseSubAgent
from subagents.services.audit_service import AuditService
from subagents.state import SubAgentState


class AuditorSubAgent(BaseSubAgent):
    """Run full legacy audit probes through subagents interface."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.audit_service = AuditService()

    def run(self, state: SubAgentState) -> SubAgentState:
        scenario_data = state.get("scenario_data", {})
        source_type = state.get("source_type")

        if source_type == "zip" and state.get("source_zip_path"):
            report = self.audit_service.audit_zip(state["source_zip_path"])
            self.log(state, f"audited zip source: {state['source_zip_path']}")
        else:
            report = self.audit_service.audit_scenario(scenario_data)
            self.log(state, "audited scenario object using probes")

        state["audit_report"] = report
        state["issues"] = self.audit_service.collect_issues(report)
        return state
