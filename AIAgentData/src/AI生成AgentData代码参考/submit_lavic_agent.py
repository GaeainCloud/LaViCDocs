import requests
from langchain_core.messages import AIMessage
from config import LAVIC_API_SERVER
from data_types.agent_entry import AgentEntry

def submit_lavic_agent_node(state: dict):
    """
    Submits the Lavic agent data to the API to create a new agent.

    Args:
        state (dict): The current state of the graph.

    Returns:
        dict: A dictionary containing the updated agent keys.
    """
    node_name = "创建仿真模型"
    print(f"---Calling {node_name} node---")
    
    messages = state.get("messages", [])
    
    # Get the auth token from the state
    auth_token = state.get("auth_token")
    if not auth_token:
        raise ValueError("Auth token not found in state")

    # Get the lavicagent_data from the state
    lavicagent_data = state.get("lavicagent_data")
    if not lavicagent_data:
        raise ValueError("Lavic agent data not found in state")

    equipment_name = lavicagent_data.get("agentName")
    messages.append(AIMessage(content=f"step_info::{node_name}::正在为 '{equipment_name}' 创建仿真模型...\n"))
    
    headers = {
        "Authorization": f"admin-Token={auth_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{LAVIC_API_SERVER}/api/v1/lavic-core/saveAgent?isGitLab=false",
        headers=headers,
        json=lavicagent_data
    )
    response.raise_for_status()
    response_data = response.json()
    agent_key = response_data["data"]
    
    messages.append(AIMessage(content=f"step_info::{node_name}::仿真模型 '{equipment_name}' 创建成功，模型KEY为 '{agent_key}'\n"))

    # Update the agent_keys list
    agent_keys = state.get("agent_keys", [])
    agent_keys.append(AgentEntry(agentkey=agent_key, equipment=equipment_name, instance_amount=0, instances=[]))

    return {"messages": messages, "agent_keys": agent_keys}
