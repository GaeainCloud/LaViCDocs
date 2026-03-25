from __future__ import annotations

from typing import Any, Dict, List


class Analyzer:
    """
    Analyzes logs vs intent.
    """

    def analyze(self, logs: list, intent: str):
        intent_tokens = [token for token in intent.split() if token]
        matched = 0
        lower_logs: List[str] = [str(line).lower() for line in logs]
        for token in intent_tokens:
            token_lower = token.lower()
            if any(token_lower in line for line in lower_logs):
                matched += 1
        score = (matched / len(intent_tokens)) if intent_tokens else 1.0
        return {
            "intent": intent,
            "log_count": len(logs),
            "intent_coverage_score": round(score, 3),
            "matched_tokens": matched,
            "total_tokens": len(intent_tokens),
        }
