import copy
import json
from pathlib import Path


EVTOL_TEMPLATE_PATH = Path(
    "/Users/qiaoyanshuo/AIProduct/codexproject/agentmodelbuilder/AIAgentData/models/大疆Matrice 300RTK无人机/agent.json"
)


def _load_evtol_template():
    data = json.loads(EVTOL_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return data[0] if isinstance(data, list) else data


def apply_evtol_mission_profile(agent):
    """Replace mission dynamics and actions with the validated eVTOL profile."""
    template = _load_evtol_template()
    agent["missionableDynamics"] = copy.deepcopy(template.get("missionableDynamics", []))
    agent["axns"] = copy.deepcopy(template.get("axns", []))
    return agent
