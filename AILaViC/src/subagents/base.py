from __future__ import annotations

from abc import ABC, abstractmethod

from subagents.state import SubAgentState, append_log


class BaseSubAgent(ABC):
    """Base contract for a subagent working on shared state."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def run(self, state: SubAgentState) -> SubAgentState:
        """Run subagent logic and return updated state."""
        raise NotImplementedError

    def log(self, state: SubAgentState, message: str) -> None:
        append_log(state, f"{self.name}: {message}")
