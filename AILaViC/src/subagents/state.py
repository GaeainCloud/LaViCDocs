from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict


class SubAgentState(TypedDict, total=False):
    user_intent: str
    input_path: str
    output_dir: str

    source_type: str
    source_path: str
    source_zip_path: str

    knowledge_context: Dict[str, Any]
    scenario_data: Dict[str, Any]
    audit_report: Dict[str, Any]
    audit_report_after_fix: Dict[str, Any]
    execution_plan: Dict[str, Any]
    debug_summary: Dict[str, Any]

    artifacts: Dict[str, str]
    issues: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
    logs: List[str]

    fixed: bool
    status: str
    current_step: str


def init_state(
    *,
    user_intent: str = "",
    input_path: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> SubAgentState:
    state: SubAgentState = {
        "user_intent": user_intent,
        "output_dir": output_dir or str(Path("outputs")),
        "logs": [],
        "warnings": [],
        "errors": [],
        "issues": [],
        "artifacts": {},
        "status": "RUNNING",
    }
    if input_path:
        state["input_path"] = input_path
    return state


def append_log(state: SubAgentState, message: str) -> None:
    logs = state.setdefault("logs", [])
    logs.append(message)

