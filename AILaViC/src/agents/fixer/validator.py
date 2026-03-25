from __future__ import annotations

from schemas.agent_data import ScenarioData


class Validator:
    """
    Quick schema validation after fixes.
    """

    def validate(self, scenario: dict) -> bool:
        try:
            ScenarioData(**scenario)
            return True
        except Exception:
            return False
