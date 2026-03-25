from __future__ import annotations

from datetime import datetime


class MCPClient:
    """
    Client for LaViC MCP Server.
    """

    def connect(self):
        return {
            "connected": False,
            "timestamp": datetime.now().isoformat(),
            "message": "MCP endpoint is not configured.",
        }
