from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    """
    Base class for all agents.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the agent.
        """
        pass
