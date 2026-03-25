from __future__ import annotations

from subagents.base import BaseSubAgent
from subagents.services.audit_service import AuditService
from subagents.services.fix_service import FixService
from subagents.state import SubAgentState


class FixerSubAgent(BaseSubAgent):
    """Apply safe auto-fixes when audit finds errors."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.audit_service = AuditService()

    def run(self, state: SubAgentState) -> SubAgentState:
        scenario_data = state.get("scenario_data", {})
        issues = state.get("issues", [])
        report = state.get("audit_report", {})
        overall_status = report.get("overall_status", "PASS")
        should_fix = overall_status == "FAIL"

        if should_fix:
            fixed_data, actions = FixService.apply_safe_fixes(scenario_data, issues)
            state["scenario_data"] = fixed_data
            state["fixed"] = bool(actions)
            state.setdefault("artifacts", {})["fix_actions"] = ", ".join(actions) if actions else ""
            self.log(state, f"applied fixes: {len(actions)}")

            # Re-audit fixed in-memory scenario so downstream gets latest quality signal.
            post_fix_report = self.audit_service.audit_scenario(fixed_data)
            state["audit_report_after_fix"] = post_fix_report
            state["issues"] = self.audit_service.collect_issues(post_fix_report)
        else:
            state["fixed"] = False
            self.log(state, "no fix required")
        return state
