from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class WaypointItem(BaseModel):
    wpsCore: List[float] = Field(default_factory=list, description="[lon, lat, alt, ...]")
    speed: float = 0.0
    
class WaypointGroup(BaseModel):
    wpsKeyword: str
    wps: List[WaypointItem] = []

class AgentInstance(BaseModel):
    agentInstId: Optional[str] = None
    agentKey: str
    agentId: Optional[str] = None
    instanceName: str
    agentType: str
    agentDesc: Optional[str] = None
    waypoints: List[WaypointGroup] = []
    fldmds: List[Dict[str, Any]] = []
    axns: List[Dict[str, Any]] = []
    
    # Allow extra fields
    class Config:
        extra = "allow"

class SimulationMeta(BaseModel):
    simulationName: str
    simulationStatus: str
    class Config:
        extra = "ignore"

class ScenarioData(BaseModel):
    simulation: Optional[SimulationMeta] = None
    agentInstances: List[AgentInstance] = []
    
    class Config:
        extra = "ignore"
