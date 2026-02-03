from langchain_core.messages import AIMessage

def construct_lavicagent_data_node(state):
    """Node to construct the lavicagent_data dictionary."""
    node_name = "构建仿真模型"
    equipment = state["current_equipment"]
    messages = state.get("messages", [])
    
    messages.append(AIMessage(content=f"step_info::{node_name}::正在构建装备 '{equipment}' 的仿真模型基础数据...\n"))
    
    lavicagent_data = {
        "agentName": equipment,
        "agentNameI18n": equipment,
        "agentType": "Instagent",
        "agentJetdsCodes": [{"agentJetdsCode": "UYK"}],
        "missionable": True,
    }
    
    # Add the lavicagent_data to the state
    state["lavicagent_data"] = lavicagent_data
    
    messages.append(AIMessage(content=f"step_info::{node_name}::装备 '{equipment}' 的仿真模型基础数据构建完成\n"))
    state["messages"] = messages
    
    return state
