from __future__ import annotations

from datetime import datetime


class Monitor:
    """
    Monitors simulation status.
    """

    def poll_status(self):
        return {
            "status": "IDLE",
            "timestamp": datetime.now().isoformat(),
            "message": "Runtime monitor is placeholder until MCP streaming is connected.",
        }
