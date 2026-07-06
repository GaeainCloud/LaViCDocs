from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config import resolve_agent_type, get_sidc, DYNAMICS_MAP, TEMPLATE_MAP


def test_resolve_agent_type_alias():
    assert resolve_agent_type("装甲车") == "vehicle"
    assert resolve_agent_type("fighter") == "aircraft"


def test_resolve_agent_type_standard():
    """标准类型名直接通过。"""
    for std_type in TEMPLATE_MAP:
        assert resolve_agent_type(std_type) == std_type


def test_resolve_agent_type_substring_chinese():
    """[P1-5] 中文子串模糊匹配。"""
    assert resolve_agent_type("无人潜航器") == "underwater"
    assert resolve_agent_type("隐身战斗机") == "aircraft"


def test_resolve_agent_type_invalid_raises():
    """[P3-7] 无效输入应抛出 ValueError。"""
    with pytest.raises(ValueError):
        resolve_agent_type("完全不存在的类型xyz")


def test_get_sidc_default_and_subtype():
    assert get_sidc("vehicle") == "Friendly Ground Vehicle"
    assert get_sidc("vehicle", "truck") == "Friendly Cargo Truck"


def test_get_sidc_unknown_subtype_returns_default():
    """未知子类型应回退到 default。"""
    assert get_sidc("vehicle", "nonexistent") == "Friendly Ground Vehicle"


def test_dynamics_map_has_vehicle_rule():
    assert DYNAMICS_MAP["vehicle"] == "iagnt_dynamics_vehicle_simple"


def test_dynamics_map_covers_all_template_types():
    """每个模板类型都应有对应的动力学规则。"""
    for agent_type in TEMPLATE_MAP:
        assert agent_type in DYNAMICS_MAP, f"Missing dynamics for: {agent_type}"
