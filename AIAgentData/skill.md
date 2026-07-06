# Simulation Model Generation & Packaging Pipeline (NLP to ZIP)

## 1. 技能概述 (Overview)
本技能定义了从自然语言描述到 LaViC 标准模型资产包（`.zip`）的自动化流程，覆盖无人机、车辆、舰船、导弹等类型。

核心目标：输入一段描述，输出可导入 LaViC 的标准 ZIP 包。

## 2. 标准流水线 (Pipeline Steps)

### 2.1 步骤一：模型定义与生成 (Definition & Generation)
- 输入：自然语言描述（名称、类型、功能）
- 处理：
  - 模板选择：根据类型映射选择 `examples/*.json`
  - JSON 构建：填充 `agentName`、`agentDesc` 等关键字段
  - 动力学映射：按规则表写入 `missionableDynamics`
  - Schema 校验：使用 `src/validator.py`
- 输出：`agent.json`

Fallback:
- 模板不存在：中止并提示可选类型
- Schema 校验失败：输出前 3 条警告信息，但**不中止**流水线（Schema 问题归为非致命警告，最终验收在步骤六中处理）

### 2.2 步骤二：资产获取与生成 (Asset Acquisition)
为每个模型准备三类资产：
1. 缩略图（Thumbnail）
   - 来源：Web Search MCP（`web-research`）
   - 策略：搜索 3-5 张候选图后评分择优
   - 版权与来源：自动跳过高版权风险图库域名（如商业素材站），优先 Wikimedia/.gov/.mil 等来源
2. 军标（Military Symbol）
   - 工具：`src/gen_mil_symbols.py` / `src/utils/mil_symbol.py`
   - 标准：NATO APP-6(D)
3. 3D 模型（GLB）
   - 来源：Rodin / Blender / 现有模型库

Fallback:
- 图片搜索失败：优化检索词后重试 2 次；仍失败则中止
- 军标生成失败：回退到默认描述 `"Friendly Unmanned Aerial Vehicle"`
- GLB 获取失败：允许人工放入 `models/downloads/{ModelName}.glb` 后继续

### 2.3 步骤三：资产标准化处理 (Asset Standardization)
- 必做几何修正（Y-Up）：
  1. X 轴 -90°（Z-Up -> Y-Up）
  2. Y 轴 180°（朝向修正）
- 工具：`src/utils/glb_utils.py`
- 幂等：通过 `*.glb.rotation_applied` 文件级标记防重复旋转

Fallback:
- GLB 不存在：记录告警并跳过该步骤（后续验收会失败）
- `trimesh` 未安装：中止并提示安装依赖

### 2.4 步骤四：目录结构与配置 (Structure & Configuration)
目录结构要求：

```text
models/
└── {ModelName}/
    ├── agent.json
    └── {ModelName}/
        ├── {ModelName}.png
        ├── {ModelName}_mil.png
        └── {ModelName}_AI_Rodin.glb
```

必须修复字段：
- 根级：`agentName`, `modelUrlSlim`, `modelUrlFat`, `modelUrlSymbols`
- `model` 对象：`modelName`, `thumbnail`, `mapIconUrl`, `dimModelUrls`

Fallback:
- JSON 缺字段：按最小可用结构自动补齐；无法补齐则中止

### 2.5 步骤五：最终打包 (Final Packaging)
- 工具：`src/zip_models.py` / `src/utils/package_utils.py`
- 要求：
  - UTF-8 ZIP
  - 扁平结构（ZIP 根目录直接包含 `agent.json` 与资源子目录）

Fallback:
- 打包失败：保留中间目录，不清理，便于排查

### 2.6 步骤六：验收检查 (Acceptance Test)
执行端到端检查：
1. ZIP 内存在 `agent.json`
2. JSON 中所有资源路径在 ZIP 内可解析
3. Schema 校验

实现：`src/pipeline.py` 的 `step6_verify` + `src/utils/package_utils.py::validate_package`

## 3. 规则映射 (Deterministic Rules)

### 3.1 模板选择决策表
| 输入类型关键词 | 标准类型 | 模板 |
| :--- | :--- | :--- |
| 车辆/装甲车/truck | `vehicle` | `examples/01vehicleAgent.json` |
| 飞机/战斗机/fighter | `aircraft` | `examples/02aircraftAgent.json` |
| 无人机/evtol/uav | `evtol` | `examples/03evtolAgent.json` |
| 潜航器/uuv/submarine | `underwater` | `examples/04underwaterVehicleAgent.json` |
| 舰船/destroyer/frigate | `ship` | `examples/05shipAgent.json` |
| 巡飞弹 | `loiter_munition` | `examples/06loiterMunitionAgent.json` |
| 导弹 | `missile` | `examples/07missileAgent.json` |
| 跳雷 | `bounding_mine` | `examples/08boundingMineAgent.json` |
| 充电站 | `charging_station` | `examples/09chargingStationAgent.json` |
| 卫星 | `satellite` | `examples/10satelliteAgent.json` |

来源：`src/config.py::TEMPLATE_MAP` 与 `TYPE_ALIASES`

### 3.2 动力学规则表
| 标准类型 | dynamics 插件 |
| :--- | :--- |
| `vehicle` | `iagnt_dynamics_vehicle_simple` |
| `aircraft` | `iagnt_dynamics_carrier_based_aircraft` |
| `evtol` | `iagnt_dynamics_evtol_simple` |
| `underwater` | `iagnt_dynamics_submarine_simple` |
| `ship` | `iagnt_dynamics_ship_simple` |
| `loiter_munition` | `iagnt_dynamics_loiter_munition` |
| `missile` | `iagnt_dynamics_missile_targeting` |
| `bounding_mine` | `iagnt_dynamics_missile_targeting` |
| `charging_station` | `iagnt_dynamics_immobility` |
| `satellite` | `iagnt_dynamics_sgp4` |

来源：`src/config.py::DYNAMICS_MAP`

### 3.3 SIDC 映射规则

每种 agent 类型均有 `default` 描述和可选子类型描述，用于生成 NATO APP-6(D) 军标：

| 标准类型 | 子类型 | 符号描述 (Symbol Description) |
| :--- | :--- | :--- |
| `vehicle` | `default` | Friendly Ground Vehicle |
| `vehicle` | `truck` | Friendly Cargo Truck |
| `vehicle` | `apc` | Friendly Armoured Fighting Vehicle |
| `vehicle` | `launcher` | Friendly Missile Launcher |
| `aircraft` | `default` | Friendly Fixed Wing |
| `aircraft` | `fighter` | Friendly Fighter |
| `aircraft` | `uav` | Friendly Unmanned Aerial Vehicle |
| `aircraft` | `recon` | Friendly Reconnaissance |
| `aircraft` | `awacs` | Friendly Airborne Early Warning |
| `aircraft` | `tanker` | Friendly Tanker Aircraft |
| `aircraft` | `bomber` | Friendly Bomber |
| `evtol` | `default` | Friendly Rotary Wing Unmanned Aerial Vehicle |
| `evtol` | `rotary` | Friendly Rotary Wing Unmanned Aerial Vehicle |
| `evtol` | `fixed` | Friendly Fixed Wing Unmanned Aerial Vehicle |
| `underwater` | `default` | Friendly Submarine |
| `underwater` | `uuv` | Friendly Unmanned Underwater Vehicle |
| `ship` | `default` | Friendly Surface Combatant |
| `ship` | `destroyer` | Friendly Destroyer |
| `ship` | `frigate` | Friendly Frigate |
| `ship` | `carrier` | Friendly Aircraft Carrier |
| `loiter_munition` | `default` | Friendly Unmanned Aerial Vehicle |
| `missile` | `default` | Friendly Missile |
| `missile` | `surface_to_surface` | Friendly Surface-to-Surface Missile |
| `missile` | `surface_to_air` | Friendly Surface-to-Air Missile |
| `missile` | `air_to_air` | Friendly Air-to-Air Missile |
| `missile` | `launcher` | Friendly Missile Launcher |
| `bounding_mine` | `default` | Friendly Mine |
| `charging_station` | `default` | Friendly Ground Vehicle |
| `satellite` | `default` | Friendly Satellite |

来源：`src/config.py::SIDC_MAP`。CLI 用法：`--sidc fighter` 选择子类型军标。

## 4. 核心脚本工具箱 (Toolbox)
| 脚本文件 | 功能 |
| :--- | :--- |
| `src/pipeline.py` | 六步统一编排器（含验收） |
| `src/config.py` | 路径/模板/SIDC/dynamics 中央配置 |
| `src/utils/image_utils.py` | 图片抓取与评分 |
| `src/utils/mil_symbol.py` | 军标生成与回退 |
| `src/utils/glb_utils.py` | GLB 旋转与幂等标记 |
| `src/utils/package_utils.py` | 路径修复、打包、验收检查 |
| `src/validator.py` | Schema 校验 |
| `src/logger.py` | 统一日志输出（替代核心脚本 print） |

## 5. MCP Server 配置指南

本流水线通过 MCP (Model Context Protocol) 连接外部服务，用于图片搜索和 3D 模型操作。

### 5.1 环境变量配置

先复制 `.env.example` 为 `.env`，填入实际值：

```bash
cp .env.example .env
```

必填项：
| 变量名 | 用途 | 获取方式 |
| :--- | :--- | :--- |
| `TAVILY_API_KEY` | Web Search（图片搜索） | https://tavily.com 注册获取 |

可选项：
| 变量名 | 用途 | 默认值 |
| :--- | :--- | :--- |
| `HTTP_PROXY` / `HTTPS_PROXY` | 网络代理 | 空（不使用代理） |
| `RODIN_API_KEY` | Rodin 3D 模型生成 API | 空 |
| `LAVIC_API_SERVER` | LaViC 平台 API 地址 | 空 |
| `LAVIC_AUTH_TOKEN` | LaViC 平台认证令牌 | 空 |

### 5.2 MCP Server 配置文件

`mcp_server_config.json` 结构如下：
```json
{
  "mcpServers": {
    "web-research": { "command": "npx", "args": [...], "env": { "TAVILY_API_KEY": "..." } },
    "blender-mcp": { "command": "uvx", "args": [...], "env": { "BLENDER_MCP_HOST": "...", "BLENDER_MCP_PORT": "..." } }
  }
}
```

已配置两个 MCP Server：

1. **`web-research`** — Tavily Web Search
   - 功能：步骤二中搜索模型缩略图
   - 依赖：`TAVILY_API_KEY` 环境变量
   - 搜索策略：3-5 张候选图 → 评分择优（`src/utils/image_utils.py`）

2. **`blender-mcp`** — Blender 3D 资产操作
   - 功能：通过 Blender 处理 3D 模型（可选）
   - 安装：将 `src/blender_mcp_addon.py` 复制到 Blender 插件目录
     - macOS: `~/Library/Application Support/Blender/{version}/scripts/addons/`
     - Windows: `%APPDATA%\Blender Foundation\Blender\{version}\scripts\addons\`
   - 在 Blender 中启用插件后，MCP Server 会自动监听连接

### 5.3 验证 MCP 连通性

```bash
# 验证 Tavily API
curl -X POST https://api.tavily.com/search \
  -H "Content-Type: application/json" \
  -d '{"api_key":"YOUR_KEY","query":"F-22 Raptor","max_results":1}'
```

## 6. AI 参考代码与主流水线集成说明

### 6.1 两套代码的关系

项目中存在两套流水线代码，各有分工：

| 维度 | 主流水线 (`src/pipeline.py`) | AI 参考代码 (`src/AI生成AgentData代码参考/`) |
| :--- | :--- | :--- |
| **核心场景** | 离线生成标准 ZIP 包 | 在线对接 LaViC API Server |
| **技术栈** | 纯 Python + 本地文件 I/O | LangChain / LangGraph + HTTP API |
| **运行模式** | CLI / 交互式 | LangGraph DAG 编排 |
| **输出物** | `models/{Name}.zip` | 直接注册到 LaViC 平台 |
| **适用阶段** | 资产准备阶段 | 平台集成阶段 |

### 6.2 共享规则复用原则

AI 参考代码必须复用主流水线的共享规则与工具，避免出现"两套规则并行"的不一致风险：

- **动力学映射**：优先使用 `src/config.py::DYNAMICS_MAP`，不在 AI 参考代码中维护独立映射
- **SIDC 符号描述**：优先使用 `src/config.py::SIDC_MAP` + `get_sidc()`
- **图像搜索/评分**：优先使用 `src/utils/image_utils.py`
- **JSON 路径修复**：优先使用 `src/utils/package_utils.py::fix_agent_json_paths()`
- **最终打包与验收**：统一走 `src/pipeline.py` 的 Step 5 + Step 6

### 6.3 参考代码文件说明

| 文件 | 功能 | 对应主流水线步骤 |
| :--- | :--- | :--- |
| `construct_lavicagent_data.py` | 构建 AgentData JSON | 步骤一 |
| `choose_dynamics.py` | 选择动力学插件 | 步骤一（动力学映射） |
| `add_image_data.py` | 添加图片资产 | 步骤二（缩略图） |
| `equipment_subgraph.py` | 装备子图构建 | 步骤一（扩展） |
| `introduce_equipment.py` | 装备参数引入 | 步骤一（扩展） |
| `submit_lavic_agent.py` | 提交至 LaViC API | 无对应（在线专用） |
| `integrated_pipeline.py` | LangGraph 完整编排 | 全流程（在线版本） |

## 7. 开发指南

### 7.1 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 TAVILY_API_KEY 等

# 3. CLI 模式生成模型包
python src/pipeline.py --name "F-22_Raptor" --type aircraft --desc "第五代隐身战斗机"

# 4. 交互式模式
python src/pipeline.py --interactive

# 5. 仅执行部分步骤
python src/pipeline.py --name "Test_Vehicle" --type vehicle --desc "测试" --steps 1,2

# 6. 运行测试
python -m pytest tests/ -v
```

### 7.2 新增装备类型检查清单

新增一种装备类型（如"直升机"）时，需同步更新以下位置：
1. `examples/` — 添加模板 JSON 文件
2. `src/config.py::TEMPLATE_MAP` — 注册模板路径
3. `src/config.py::TYPE_ALIASES` — 添加中英文关键词别名
4. `src/config.py::DYNAMICS_MAP` — 注册动力学插件
5. `src/config.py::SIDC_MAP` — 注册 NATO 符号描述
6. `skill.md §3.1` — 更新模板选择决策表
7. `skill.md §3.2` — 更新动力学规则表
