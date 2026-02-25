from typing import List, Dict, Any
import heapq

class SimulationEvent:
    def __init__(self, time: float, agent_id: str, action: str, params: Dict[str, Any] = None):
        self.time = time
        self.agent_id = agent_id
        self.action = action
        self.params = params or {}

    def __lt__(self, other):
        return self.time < other.time

class Timeline:
    """
    简易离散事件时间轴，用于逻辑审计
    """
    def __init__(self):
        self.events = []
        
    def add_event(self, time: float, agent_id: str, action: str, params: Dict = None):
        event = SimulationEvent(time, agent_id, action, params)
        heapq.heappush(self.events, event)
        
    def get_sorted_events(self) -> List[SimulationEvent]:
        """返回按时间排序的事件列表 (不破坏堆结构)"""
        return sorted(self.events)

    def clear(self):
        self.events = []
