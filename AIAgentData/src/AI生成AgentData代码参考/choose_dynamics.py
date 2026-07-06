import os
import sys
from pathlib import Path
import requests
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage
from data_types.lavic_agent_data import LavicAgentData
from utils.llm_utils import get_llm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import LAVIC_API_SERVER, DYNAMICS_MAP, TYPE_ALIASES
from logger import get_logger

log = get_logger(__name__)


class ChosenDynamics(BaseModel):
    """Structured output for the chosen dynamics plugin."""
    plugin_name: str = Field(description="The name of the most appropriate dynamics plugin.")


def _rule_pick_dynamics(equipment: str) -> str:
    """基于关键词规则优先选择 dynamics，避免不必要的 LLM 调用。"""
    if not equipment:
        return ""

    text = equipment.lower()
    for alias, agent_type in TYPE_ALIASES.items():
        if alias.lower() in text:
            return DYNAMICS_MAP.get(agent_type, "")
    return ""


def choose_dynamics(state: dict):
    """
    Chooses the most appropriate dynamics for the given equipment.

    Args:
        state (dict): The current state of the agent.

    Returns:
        dict: An empty dictionary.
    """
    node_name = "选择动力学"
    log.info("---Choosing dynamics---")
    
    messages = state.get("messages", [])
    equipment = state.get("current_equipment")
    
    messages.append(AIMessage(content=f"step_info::{node_name}::正在为装备 '{equipment}' 选择合适的动力学模型...\n"))
    
    # Get the auth token from the state
    auth_token = state.get("auth_token")
    if not auth_token:
        raise ValueError("Auth token not found in state")

    messages.append(AIMessage(content=f"step_info::{node_name}::正在获取可用的动力学插件列表...\n"))

    # Call the Lavic API to get dynamics plugins
    headers = {"Authorization": f"admin-Token={auth_token}"}
    response = requests.get(
        f"{LAVIC_API_SERVER}/api/v1/lavic-core/getPluginByType?pluginType=dynamics",
        headers=headers,
    )
    response.raise_for_status()
    dynamics_plugins = response.json()["data"]["content"]

    # Create a map of plugin names to introductions
    plugin_introductions = {
        plugin["pluginName"]: plugin["pluginObjectSetting"]["pluginDescription"]["introduction"]
        for plugin in dynamics_plugins
    }

    if not equipment:
        raise ValueError("Equipment not found in state")

    messages.append(AIMessage(content=f"step_info::{node_name}::已获取 {len(dynamics_plugins)} 个动力学插件，正在分析最适合的插件...\n"))

    # 先走规则映射；规则未命中再走 LLM 兜底
    chosen_dynamics = _rule_pick_dynamics(equipment)
    if chosen_dynamics:
        messages.append(AIMessage(content=f"step_info::{node_name}::规则命中动力学插件: {chosen_dynamics}\n"))
    else:
        # Create the prompt for the LLM
        prompt = f"""
        Given the following equipment:
        {equipment}

        And the following available dynamics plugins:
        {plugin_introductions}

        Which dynamics plugin is the most appropriate? Please return only the plugin name.
        
        You must return the results in the following JSON format:
        {{
            "plugin_name": "the_chosen_plugin_name"
        }}
        """

        # Call the LLM to get the most appropriate plugin name
        llm = get_llm(ChosenDynamics)
        result = llm.invoke(prompt)
        chosen_dynamics = result.plugin_name

    log.info(f"---Chosen dynamics: {chosen_dynamics}---")

    # Find the chosen plugin from the list
    chosen_plugin = next(
        (
            plugin
            for plugin in dynamics_plugins
            if plugin["pluginName"] == chosen_dynamics
        ),
        None,
    )

    if not chosen_plugin:
        raise ValueError(f"Plugin {chosen_dynamics} not found in the list")

    messages.append(AIMessage(content=f"step_info::{node_name}::已选择动力学插件: {chosen_dynamics}\n"))

    # Construct the new dynamics object
    new_dynamic = {
        "dynAsDefault": True,
        "dynKeyword": chosen_dynamics,
        "dynPluginName": chosen_dynamics,
        "dynSettings": {
            "pluginDefaultSettings": chosen_plugin["pluginSettings"],
            "pluginName": chosen_dynamics,
            "pluginNote": chosen_plugin["pluginObjectSetting"]["pluginNote"],
            "pluginNoteI18n": chosen_plugin["pluginObjectSetting"]["pluginNoteI18n"],
            "pluginSignature": chosen_plugin["pluginObjectSetting"]["pluginSignature"],
        },
    }

    # Get the lavicagent_data from the state and update it
    lavicagent_data = state.get("lavicagent_data", {})
    if "missionableDynamics" not in lavicagent_data:
        lavicagent_data["missionableDynamics"] = []
    lavicagent_data["missionableDynamics"].append(new_dynamic)

    messages.append(AIMessage(content=f"step_info::{node_name}::装备 '{equipment}' 的动力学模型配置完成\n"))

    return {"messages": messages, "lavicagent_data": lavicagent_data}
