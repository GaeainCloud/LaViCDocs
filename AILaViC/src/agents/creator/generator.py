from __future__ import annotations

from subagents.creator_subagent import CreatorSubAgent
from subagents.state import init_state


class Generator:
    """
    Backward-compatible creator wrapper.
    """

    def generate(self, intent: str) -> dict:
        state = init_state(user_intent=intent)
        state["knowledge_context"] = {"intent": intent, "mode": "generate", "hints": []}
        state["scenario_data"] = {}
        subagent = CreatorSubAgent("creator")
        output = subagent.run(state)
        return output.get("scenario_data", {})
