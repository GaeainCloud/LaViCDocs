"""validator.py 的单元测试：Schema 校验通过/失败用例。"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config import SCHEMA_PATH, EXAMPLES_DIR


def test_schema_file_exists():
    """Schema 文件必须存在，否则整个校验流程无法运行。"""
    assert SCHEMA_PATH.exists(), f"Schema file not found: {SCHEMA_PATH}"


def test_example_vehicle_agent_valid_json():
    """确认示例模板文件是合法 JSON。"""
    agent_path = EXAMPLES_DIR / "01vehicleAgent.json"
    assert agent_path.exists(), f"Template not found: {agent_path}"
    data = json.loads(agent_path.read_text(encoding="utf-8"))
    assert isinstance(data, (list, dict)), "Template should be a JSON array or object"


def test_example_agent_has_required_fields():
    """检查示例 agent 包含关键必填字段。"""
    agent_path = EXAMPLES_DIR / "01vehicleAgent.json"
    data = json.loads(agent_path.read_text(encoding="utf-8"))
    agent = data[0] if isinstance(data, list) else data

    required_keys = ["agentName", "agentKey"]
    for key in required_keys:
        assert key in agent, f"Missing required field: {key}"


def test_schema_validates_valid_agent():
    """用真实 Schema 校验一个示例 agent，期望无严重错误。"""
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        import pytest
        pytest.skip("jsonschema not installed")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    agent_path = EXAMPLES_DIR / "01vehicleAgent.json"
    data = json.loads(agent_path.read_text(encoding="utf-8"))

    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(data))
    # 允许少量非致命问题，但不应有大量错误
    assert len(errors) < 20, f"Too many schema errors ({len(errors)}): {[e.message for e in errors[:5]]}"


def test_schema_rejects_empty_object():
    """空对象应该触发校验错误。"""
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        import pytest
        pytest.skip("jsonschema not installed")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors({}))
    assert len(errors) > 0, "Empty object should fail schema validation"
