from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from nodes.introduce_equipment import introduce_equipment_node
from nodes.construct_lavicagent_data import construct_lavicagent_data_node
from nodes.add_image_data import add_image_data
from nodes.choose_dynamics import choose_dynamics
from nodes.submit_lavic_agent import submit_lavic_agent_node
from nodes.search_equipment_info import search_equipment_info
from nodes.text_to_model import text_to_model
from nodes.check_equipment_exists import check_equipment_exists
from nodes.add_actions import add_actions
from data_types.lavic_agent_data import LavicAgentData

from data_types.agent_entry import AgentEntry

class EquipmentSubgraphState(TypedDict):
    """State definition for the equipment processing subgraph"""
    messages: List[BaseMessage]
    current_equipment: str
    equipment_introductions: List[Dict[str, str]]
    lavicagent_data: LavicAgentData
    auth_token: str
    tenant_id: str
    agent_keys: List[AgentEntry]
def should_process_action(state):
    """Determine if the action should be processed. If not existing, end the graph."""
    if state["existing_equipment"]:
        return "process"
    else:
        return "skip"
    
def create_equipment_subgraph():
    """Create the equipment processing subgraph"""
    workflow = StateGraph(EquipmentSubgraphState)
    workflow.add_node("introduce_equipment", introduce_equipment_node)
    workflow.add_node("construct_lavicagent_data", construct_lavicagent_data_node)
    workflow.add_node("add_image_data", add_image_data)
    workflow.add_node("choose_dynamics", choose_dynamics)
    workflow.add_node("submit_lavic_agent", submit_lavic_agent_node)
    workflow.set_entry_point("introduce_equipment")
    workflow.add_edge("introduce_equipment", "construct_lavicagent_data")
    workflow.add_edge("construct_lavicagent_data", "add_image_data")
    workflow.add_edge("add_image_data", "choose_dynamics")
    workflow.add_edge("choose_dynamics", "submit_lavic_agent")
    workflow.add_edge("submit_lavic_agent", END)
    return workflow.compile()

def create_equipment_subgraph_v2():
    """Create the equipment processing subgraph"""
    workflow = StateGraph(EquipmentSubgraphState)
    workflow.add_node("construct_lavicagent_data", construct_lavicagent_data_node)
    workflow.add_node("search_equipment_info", search_equipment_info)
    workflow.add_node("add_image_data", add_image_data)
    workflow.add_node("choose_dynamics", choose_dynamics)
    workflow.add_node("text_to_model", text_to_model)
    workflow.add_node("check_equipment_exists", check_equipment_exists)
    workflow.add_node("submit_lavic_agent", submit_lavic_agent_node)
    workflow.add_node("add_actions", add_actions)

    workflow.set_entry_point("search_equipment_info")
    workflow.add_edge("search_equipment_info", "construct_lavicagent_data")
    workflow.add_edge("construct_lavicagent_data", "add_image_data")
    workflow.add_edge("add_image_data", "text_to_model")
    workflow.add_edge("text_to_model", "choose_dynamics")
    workflow.add_edge("choose_dynamics", "check_equipment_exists")
    workflow.add_conditional_edges(
        "check_equipment_exists",
        should_process_action,
        {
            "process": "add_actions",
            "skip": "submit_lavic_agent"
        }
    )

    workflow.add_edge("add_actions", "submit_lavic_agent")
    workflow.add_edge("submit_lavic_agent", END)
    return workflow.compile()
