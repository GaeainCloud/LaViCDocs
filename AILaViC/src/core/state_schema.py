from typing import Any, Dict, List, TypedDict

class SharedState(TypedDict):
    """
    Shared state across subagents pipeline.
    """
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
    fixed: bool
    status: str

    logs: List[str]
    current_step: str
