from __future__ import annotations

from datetime import datetime

from subagents.base import BaseSubAgent
from subagents.services.io_service import ScenarioIOService
from subagents.state import SubAgentState


class CreatorSubAgent(BaseSubAgent):
    """Load existing scenario or generate scenario skeleton from intent."""

    def run(self, state: SubAgentState) -> SubAgentState:
        intent = state.get("user_intent", "").strip() or "通用想定"
        context = state.get("knowledge_context", {})
        input_path = state.get("input_path")

        if input_path:
            scenario_data, source_meta = ScenarioIOService.load_scenario(input_path)
            state["source_type"] = source_meta["source_type"]
            state["source_path"] = source_meta["source_path"]
            if "source_zip_path" in source_meta:
                state["source_zip_path"] = source_meta["source_zip_path"]
            self.log(state, f"loaded scenario from {source_meta['source_type']}")
        else:
            scenario_data = {
                "simulation": {
                    "simulationName": f"AI生成想定-{intent[:24]}",
                    "simulationStatus": "DRAFT",
                },
                "agentInstances": [],
                "meta": {
                    "intent": intent,
                    "hints": context.get("hints", []),
                    "generated_at": datetime.now().isoformat(),
                },
            }
            state["source_type"] = "generated"
            state["source_path"] = "in_memory"
            self.log(state, "generated scenario skeleton from intent")

        state["scenario_data"] = scenario_data
        return state
