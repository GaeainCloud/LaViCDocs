from __future__ import annotations

from subagents.base import BaseSubAgent
from subagents.state import SubAgentState


class DebuggerSubAgent(BaseSubAgent):
    """Generate post-run diagnostics summary."""

    def run(self, state: SubAgentState) -> SubAgentState:
        logs = state.get("logs", [])
        audit = state.get("audit_report_after_fix") or state.get("audit_report", {})
        issues = state.get("issues", [])
        high_severity = [
            issue for issue in issues if (issue.get("severity") or "").upper() in {"ERROR", "CRITICAL", "FAIL"}
        ]
        warnings = [
            issue for issue in issues if (issue.get("severity") or "").upper() in {"WARN", "WARNING"}
        ]

        state["debug_summary"] = {
            "steps": len(logs) + 1,
            "audit_status": audit.get("overall_status", "UNKNOWN"),
            "issue_count": len(issues),
            "high_severity_issue_count": len(high_severity),
            "warning_issue_count": len(warnings),
            "last_log": logs[-1] if logs else "",
        }
        self.log(state, "summary generated")
        return state
