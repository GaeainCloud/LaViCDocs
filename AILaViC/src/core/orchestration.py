from __future__ import annotations

from typing import Any, Dict

from core.subagent_orchestrator import SubAgentOrchestrator


class Orchestrator:
    """
    Backward-compatible wrapper.
    Legacy callers can still import Orchestrator from this module.
    """

    def __init__(self) -> None:
        self.impl = SubAgentOrchestrator()

    def run(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        return self.impl.run(initial_state)
