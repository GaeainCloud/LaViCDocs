"""
AIAgentData 中央配置模块
消除所有硬编码路径，统一管理路径、映射表和环境变量。
"""
import os
from pathlib import Path

# ============================================================
# 路径配置（跨平台，基于项目根目录自动推导）
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
MODELS_DIR = PROJECT_ROOT / "models"
DOWNLOADS_DIR = MODELS_DIR / "downloads"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
DOCS_DIR = PROJECT_ROOT / "docs"
SCHEMA_PATH = SRC_DIR / "校验代码参考" / "AgentData_schema.json"

# ============================================================
# 环境变量配置（不硬编码敏感信息）
# ============================================================
PROXY_URL = os.environ.get("HTTP_PROXY", "")
HTTPS_PROXY_URL = os.environ.get("HTTPS_PROXY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
RODIN_API_KEY = os.environ.get("RODIN_API_KEY", "")
LAVIC_API_SERVER = os.environ.get("LAVIC_API_SERVER", "")
LAVIC_AUTH_TOKEN = os.environ.get("LAVIC_AUTH_TOKEN", "")

# ============================================================
# 模板选择决策表 [#2]
# 根据 agent 类型选择对应的 JSON 模板
# ============================================================
TEMPLATE_MAP = {
    "vehicle": EXAMPLES_DIR / "01vehicleAgent.json",
    "aircraft": EXAMPLES_DIR / "02aircraftAgent.json",
    "evtol": EXAMPLES_DIR / "03evtolAgent.json",
    "underwater": EXAMPLES_DIR / "04underwaterVehicleAgent.json",
    "ship": EXAMPLES_DIR / "05shipAgent.json",
    "loiter_munition": EXAMPLES_DIR / "06loiterMunitionAgent.json",
    "missile": EXAMPLES_DIR / "07missileAgent.json",
    "bounding_mine": EXAMPLES_DIR / "08boundingMineAgent.json",
    "charging_station": EXAMPLES_DIR / "09chargingStationAgent.json",
    "satellite": EXAMPLES_DIR / "10satelliteAgent.json",
}

# 类型别名 → 标准类型映射（支持中文关键词匹配）
TYPE_ALIASES = {
    # 车辆
    "车辆": "vehicle", "装甲车": "vehicle", "卡车": "vehicle",
    "战车": "vehicle", "地面车辆": "vehicle", "ground vehicle": "vehicle",
    "truck": "vehicle", "armored vehicle": "vehicle",
    # 飞机
    "飞机": "aircraft", "客机": "aircraft", "舰载机": "aircraft",
    "战斗机": "aircraft", "fighter": "aircraft", "carrier aircraft": "aircraft",
    # eVTOL
    "evtol": "evtol", "多旋翼": "evtol", "垂起": "evtol",
    "无人机": "evtol", "旋翼机": "evtol", "vtol": "evtol",
    "drone": "evtol", "uav": "evtol",
    # 水下
    "潜航器": "underwater", "水下无人": "underwater", "uuv": "underwater",
    "submarine": "underwater", "underwater vehicle": "underwater",
    # 舰船
    "舰船": "ship", "驱逐舰": "ship", "护卫舰": "ship",
    "destroyer": "ship", "frigate": "ship",
    # 巡飞弹
    "巡飞弹": "loiter_munition", "游荡弹药": "loiter_munition",
    "loiter munition": "loiter_munition",
    # 导弹
    "导弹": "missile", "missile": "missile",
    # 跳雷
    "跳雷": "bounding_mine", "地雷": "bounding_mine",
    "mine": "bounding_mine",
    # 充电站
    "充电站": "charging_station", "charging station": "charging_station",
    # 卫星
    "卫星": "satellite", "satellite": "satellite",
}

# ============================================================
# 动力学选择规则表 [#4]
# agent 类型 → dynamics 插件名称
# ============================================================
DYNAMICS_MAP = {
    "vehicle": "iagnt_dynamics_vehicle_simple",
    "aircraft": "iagnt_dynamics_carrier_based_aircraft",
    "evtol": "iagnt_dynamics_evtol_simple",
    "underwater": "iagnt_dynamics_submarine_simple",
    "ship": "iagnt_dynamics_ship_simple",
    "loiter_munition": "iagnt_dynamics_loiter_munition",
    "missile": "iagnt_dynamics_missile_targeting",
    "bounding_mine": "iagnt_dynamics_missile_targeting",
    "charging_station": "iagnt_dynamics_immobility",
    "satellite": "iagnt_dynamics_sgp4",
}

# ============================================================
# SIDC 代码映射表 [#3]
# NATO APP-6(D) 符号描述
# ============================================================
SIDC_MAP = {
    "vehicle": {
        "default": "Friendly Ground Vehicle",
        "armored": "Friendly Armoured Fighting Vehicle",
        "truck": "Friendly Cargo Truck",
        "reconnaissance": "Friendly Reconnaissance Vehicle",
    },
    "aircraft": {
        "default": "Friendly Fixed Wing",
        "fighter": "Friendly Fighter",
        "awacs": "Friendly Airborne Early Warning",
        "tanker": "Friendly Tanker Aircraft",
        "bomber": "Friendly Bomber",
    },
    "evtol": {
        "default": "Friendly Rotary Wing Unmanned Aerial Vehicle",
        "rotary": "Friendly Rotary Wing Unmanned Aerial Vehicle",
        "fixed": "Friendly Fixed Wing Unmanned Aerial Vehicle",
    },
    "underwater": {
        "default": "Friendly Submarine",
        "uuv": "Friendly Unmanned Underwater Vehicle",
    },
    "ship": {
        "default": "Friendly Surface Combatant",
        "destroyer": "Friendly Destroyer",
        "frigate": "Friendly Frigate",
        "carrier": "Friendly Aircraft Carrier",
    },
    "loiter_munition": {
        "default": "Friendly Unmanned Aerial Vehicle",
    },
    "missile": {
        "default": "Friendly Missile",
        "surface_to_surface": "Friendly Surface-to-Surface Missile",
        "surface_to_air": "Friendly Surface-to-Air Missile",
        "air_to_air": "Friendly Air-to-Air Missile",
        "launcher": "Friendly Missile Launcher",
    },
    "bounding_mine": {
        "default": "Friendly Mine",
    },
    "charging_station": {
        "default": "Friendly Ground Vehicle",
    },
    "satellite": {
        "default": "Friendly Satellite",
    },
}

# ============================================================
# 3D 模型处理配置
# ============================================================
# 旋转幂等标记后缀（按 GLB 文件粒度，如 xxx.glb.rotation_applied）
GLB_ROTATION_MARKER = ".rotation_applied"
DEFAULT_GLB_SUFFIX = "_AI_Rodin.glb"
DEFAULT_MIL_SUFFIX = "_mil.png"

# ============================================================
# 图片搜索配置
# ============================================================
IMAGE_SEARCH_MAX_CANDIDATES = 5
IMAGE_MIN_WIDTH = 400
IMAGE_MIN_HEIGHT = 300
IMAGE_MAX_ASPECT_RATIO = 2.5
IMAGE_MIN_ASPECT_RATIO = 0.5

# 版权/来源风险控制
# 命中 BLOCKED 则直接跳过；PREFERRED 提高评分；LOW_TRUST 降低评分
IMAGE_BLOCKED_COPYRIGHT_DOMAINS = (
    "gettyimages.com",
    "shutterstock.com",
    "istockphoto.com",
    "alamy.com",
    "depositphotos.com",
    "123rf.com",
)
IMAGE_PREFERRED_LICENSE_DOMAINS = (
    "wikimedia.org",
    "wikipedia.org",
    ".gov",
    ".mil",
    "nasa.gov",
)
IMAGE_LOW_TRUST_DOMAINS = (
    "pinterest.com",
    "instagram.com",
    "facebook.com",
)


def resolve_agent_type(keyword: str) -> str:
    """将用户输入的关键词解析为标准 agent 类型。

    支持精确匹配和中文子串模糊匹配。

    Args:
        keyword: 用户输入（中文/英文均可）

    Returns:
        标准类型字符串

    Raises:
        ValueError: 无法识别的类型
    """
    keyword_lower = keyword.lower().strip()
    # 1. 精确匹配标准类型名
    if keyword_lower in TEMPLATE_MAP:
        return keyword_lower
    # 2. 精确匹配别名
    if keyword_lower in TYPE_ALIASES:
        return TYPE_ALIASES[keyword_lower]
    # 3. [P1-5] 中文子串模糊匹配（如"无人潜航器"包含"潜航器"）
    for alias, std_type in TYPE_ALIASES.items():
        if alias in keyword_lower or keyword_lower in alias:
            return std_type
    raise ValueError(
        f"无法识别的 agent 类型: '{keyword}'。"
        f"支持的类型: {', '.join(TEMPLATE_MAP.keys())}"
    )


def get_sidc(agent_type: str, subtype: str = "default") -> str:
    """获取 NATO APP-6(D) 符号描述。

    Args:
        agent_type: 标准 agent 类型
        subtype: 子类型（默认 "default"）

    Returns:
        符号描述字符串
    """
    type_map = SIDC_MAP.get(agent_type, {})
    return type_map.get(subtype, type_map.get("default", "Friendly Unmanned Aerial Vehicle"))


def apply_proxy_env():
    """按环境变量统一设置代理（若为空则不设置）。"""
    if PROXY_URL:
        os.environ["HTTP_PROXY"] = PROXY_URL
    if HTTPS_PROXY_URL:
        os.environ["HTTPS_PROXY"] = HTTPS_PROXY_URL


def require_rodin_api_key() -> str:
    """获取 Rodin API Key，不存在时抛错。"""
    if not RODIN_API_KEY:
        raise ValueError("RODIN_API_KEY environment variable not set")
    return RODIN_API_KEY
