from langchain_core.messages import AIMessage
from utils.llm_utils import get_llm

def introduce_equipment_node(state):
    """Node to introduce/describe an equipment using LLM"""
    node_name = "生成装备介绍"
    equipment = state["current_equipment"]
    messages = state.get("messages", [])
    
    messages.append(AIMessage(content=f"step_info::{node_name}::正在为装备 '{equipment}' 生成介绍信息...\n"))
    
    introduction_prompt = f"""
    Please provide a brief introduction and description of the equipment: {equipment}
    
    Include information such as:
    - Type of equipment (aircraft, tank, rifle, etc.)
    - Country of origin
    - Key specifications or features
    - Notable characteristics or capabilities
    
    Keep the introduction concise but informative, around 2-3 sentences.
    """
    
    llm = get_llm()
    result = llm.invoke(introduction_prompt)
    
    # Add the introduction to the equipment introductions list
    equipment_introductions = state.get("equipment_introductions", [])
    introduction_text = result.content if hasattr(result, 'content') else str(result)
    equipment_introductions.append({
        "equipment": equipment,
        "introduction": introduction_text
    })
    
    messages.append(AIMessage(content=f"step_info::{node_name}::装备 '{equipment}' 介绍生成完成\n"))
    
    return {
        "messages": messages,
        "equipment_introductions": equipment_introductions
    }
