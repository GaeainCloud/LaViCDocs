from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END

class SharedState(TypedDict):
    """
    Shared state between agents.
    """
    user_intent: str
    scenario_data: Dict[str, Any]
    audit_report: Dict[str, Any]
    logs: List[str]
    current_step: str
