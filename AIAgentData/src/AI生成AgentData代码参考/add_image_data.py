from tavily import TavilyClient
import os
from langchain_core.messages import AIMessage
from data_types.lavic_agent_data import LavicAgentData

def add_image_data(state):
    """
    Adds image data to the lavicagent_data state.

    Args:
        state (LavicAgentData): The current state of the lavicagent.

    Returns:
        LavicAgentData: The updated state with image data.
    """
    node_name = "添加图像"
    messages = state.get("messages", [])
    query = state['current_equipment']
    
    messages.append(AIMessage(content=f"step_info::{node_name}::正在为装备 '{query}' 搜索图像数据...\n"))
    
    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY environment variable not set")

    client = TavilyClient(api_key=tavily_api_key)
    
    if not query:
        messages.append(AIMessage(content=f"step_info::{node_name}::未找到装备信息，跳过图像搜索\n"))
        state["messages"] = messages
        return state

    response = client.search(
        query=query,
        max_results=1,
        include_images=True
    )

    if response and response.get("images"):
        image_url = response["images"][0]
        print(f"Image URL for {query}: {image_url}")
        if "modelUrlSymbols" not in state['lavicagent_data'] or not state['lavicagent_data']["modelUrlSymbols"]:
            state['lavicagent_data']["modelUrlSymbols"] = []
        
        state['lavicagent_data']["modelUrlSymbols"].append({
            "symbolName": image_url,
            "symbolSeries": 0,
            "thumbnail": image_url
        })

        if "model" not in state['lavicagent_data'] or not state['lavicagent_data']["model"]:
            state['lavicagent_data']["model"] = {}
        if "thumbnail" not in state['lavicagent_data']["model"]:
            state['lavicagent_data']["model"]["thumbnail"] = {}
        sig = image_url.split("/")[-1]
        state['lavicagent_data']["model"]["thumbnail"] = {
            "url": image_url,
            "selected": True,
            "bucket": "lavic",
            "ossSig": sig
        }
        
        messages.append(AIMessage(content=f"step_info::{node_name}::装备 '{query}' 图像数据添加完成\n"))
    else:
        messages.append(AIMessage(content=f"step_info::{node_name}::未找到装备 '{query}' 的图像数据\n"))

    state["messages"] = messages
    return state
