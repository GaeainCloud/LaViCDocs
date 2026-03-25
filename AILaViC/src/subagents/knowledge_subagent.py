from __future__ import annotations

from pathlib import Path
from typing import List

from subagents.base import BaseSubAgent
from subagents.state import SubAgentState

class KnowledgeSubAgent(BaseSubAgent):
    """Collect domain hints, mode, and constraints from runtime context."""

    def run(self, state: SubAgentState) -> SubAgentState:
        intent = state.get("user_intent", "").strip()
        input_path = state.get("input_path", "").strip()

        hints: List[str] = []
        if "防空" in intent or "反导" in intent:
            hints.append("优先检查探测-拦截链路闭环。")
            hints.append("重点关注弹道与拦截弹时空一致性。")
        if "演练" in intent or "想定" in intent:
            hints.append("确保包含阶段目标、触发条件和终止条件。")
        if input_path:
            hints.append("检测输入想定与审计模式，保留源文件溯源信息。")
        if not hints:
            hints.append("使用通用战术想定模板。")

        mode = "generate"
        resolved_input = ""
        if input_path:
            resolved_input = str(Path(input_path).expanduser().resolve())
            mode = "audit_existing"

        state["knowledge_context"] = {
            "intent": intent,
            "mode": mode,
            "resolved_input_path": resolved_input,
            "hints": hints,
        }
        self.log(state, f"context collected (mode={mode})")
        return state
