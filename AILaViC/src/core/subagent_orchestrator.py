from __future__ import annotations

from typing import List

from subagents import (
    AuditorSubAgent,
    CreatorSubAgent,
    DebuggerSubAgent,
    FixerSubAgent,
    KnowledgeSubAgent,
    OperatorSubAgent,
)
from subagents.base import BaseSubAgent
from subagents.state import SubAgentState


class SubAgentOrchestrator:
    """Linear subagent orchestrator for scenario generation and audit."""

    def __init__(self) -> None:
        self.subagents: List[BaseSubAgent] = [
            KnowledgeSubAgent("knowledge"),
            CreatorSubAgent("creator"),
            AuditorSubAgent("auditor"),
            FixerSubAgent("fixer"),
            OperatorSubAgent("operator"),
            DebuggerSubAgent("debugger"),
        ]

    def run(self, initial_state: SubAgentState) -> SubAgentState:
        state = dict(initial_state)
        state.setdefault("logs", [])
        state.setdefault("warnings", [])
        state.setdefault("errors", [])
        state.setdefault("artifacts", {})
        state["status"] = "RUNNING"

        for agent in self.subagents:
            state["current_step"] = agent.name
            try:
                state = agent.run(state)
            except Exception as exc:
                state["status"] = "FAILED"
                state.setdefault("errors", []).append(f"{agent.name}: {exc}")
                state["logs"].append(f"{agent.name}: failed - {exc}")
                break
        else:
            state["status"] = "SUCCEEDED"
        return state
