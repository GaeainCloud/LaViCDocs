from __future__ import annotations

from subagents.services.fix_service import FixService


class Surgeon:
    """
    Backward-compatible fixer wrapper.
    """

    def heal(self, scenario: dict, issues: list) -> dict:
        fixed, _actions = FixService.apply_safe_fixes(scenario, issues)
        return fixed
