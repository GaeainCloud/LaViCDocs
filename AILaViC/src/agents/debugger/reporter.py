from __future__ import annotations


class Reporter:
    """
    Generates attribution reports.
    """

    def report(self, analysis_result):
        score = analysis_result.get("intent_coverage_score", 0.0)
        status = "GOOD" if score >= 0.7 else "WEAK"
        return {
            "status": status,
            "analysis": analysis_result,
            "message": f"Intent coverage score={score}",
        }
