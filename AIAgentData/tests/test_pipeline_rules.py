from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pipeline import apply_dynamics_rule


def test_apply_dynamics_rule_updates_existing_missionable():
    agent = {
        "missionableDynamics": [
            {
                "dynPluginName": "old_plugin",
                "dynKeyword": "old_keyword",
                "dynSettings": {"pluginName": "old_plugin"},
            }
        ]
    }

    chosen = apply_dynamics_rule(agent, "vehicle")

    assert chosen == "iagnt_dynamics_vehicle_simple"
    dyn = agent["missionableDynamics"][0]
    assert dyn["dynPluginName"] == "iagnt_dynamics_vehicle_simple"
    assert dyn["dynKeyword"] == "iagnt_dynamics_vehicle_simple"
    assert dyn["dynSettings"]["pluginName"] == "iagnt_dynamics_vehicle_simple"


def test_apply_dynamics_rule_creates_minimal_structure_if_missing():
    agent = {}
    chosen = apply_dynamics_rule(agent, "missile")

    assert chosen == "iagnt_dynamics_missile_targeting"
    assert len(agent["missionableDynamics"]) == 1
    assert agent["missionableDynamics"][0]["dynPluginName"] == "iagnt_dynamics_missile_targeting"
