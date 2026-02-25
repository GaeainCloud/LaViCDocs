# PRD - LaViC MCP 探索分析能力（Story1）

> 文档用途：作为当前实现版本的需求与验收基线。
> 版本：v0.2.0（与当前代码对齐）
> 更新时间：2026-02-25

---

## 1. 目标与范围

### 1.1 Story1 目标

通过自然语言完成一条可执行闭环：
- 查询模型/想定
- 控制想定运行
- 下载运行记录并解压
- 基于导出数据进行探索性分析

### 1.2 In Scope（当前版本）

- 模型/想定查询（支持分页与 `fetch_all`）
- 想定控制（`start/pause/resume/stop`）
- 运行记录下载与 ZIP 解压
- 会话内探索性分析输出（由助手基于导出数据生成）
- 想定倍速控制（`set_simulation_speed`）

### 1.3 Out of Scope（当前版本）

- 自动化分析引擎（独立脚本/报表服务）
- 完整审计平台与指标看板
- 多用户并发控制仲裁

---

## 2. 功能需求（与代码一致）

| 需求ID | 模块 | 标题 | 对应能力 |
|---|---|---|---|
| REQ-001 | 查询 | 查询模型案例与想定案例 | `list_models`、`list_scenarios` |
| REQ-002 | 控制 | 控制想定运行状态 | `control_scenario` |
| REQ-003 | 数据获取 | 下载运行记录并直接用于分析 | `download_record_data` |
| REQ-004 | 分析 | 基于运行数据输出探索性结论 | 会话分析流程 |
| REQ-005 | 接入配置 | 标准化 MCP 部署与配置 | `README.md` + `.env.example` |
| REQ-006 | 仿真控制增强 | 调整运行中的仿真倍速 | `set_simulation_speed` |

### REQ-001 查询模型案例与想定案例

- 支持关键词筛选（模型）
- 支持分页
- 支持 `fetch_all=True` 拉全量
- 想定查询默认 `simulationTag=1`（可传空字符串切换用户想定）

**验收标准**
1. 可返回模型/想定列表。
2. 返回包含关键字段（如 `simulationSig`/`agentKey`、名称、状态）。
3. 分页场景下可完整拉取。

### REQ-002 控制想定运行（start/pause/resume/stop）

- 支持动作：`start`、`pause`、`resume`、`stop`
- `pause/resume/stop` 未显式传 `record_id` 时，自动尝试定位运行记录

**验收标准**
1. 四类动作均可发起。
2. 无可用运行记录时返回明确错误信息。
3. 返回原始接口响应用于追踪。

### REQ-003 下载运行记录并用于分析

- 调用 `/getRecordData` 下载 ZIP
- 自动解压到本地目录
- 返回本地路径与文件列表

**验收标准**
1. 下载成功后可获得可解析文件。
2. ZIP 自动解压成功。
3. 失败时返回错误码/错误信息。

### REQ-004 探索性分析输出

- 当前由会话层完成，不作为独立 MCP 工具
- 最低输出结构：数据概览、关键发现、结论
- 支持继续追问迭代

**验收标准**
1. 输出包含“概览/发现/结论”。
2. 可关联到输入记录或文件路径。
3. 支持追问补充分析。

### REQ-005 标准化部署与客户端配置

- 提供 `.env.example`
- README 提供最小可用接入步骤
- 发布时排除 `.env` 与 `__pycache__`

**验收标准**
1. 新用户可按 README 完成接入。
2. 配置项覆盖 `base_url/user_id/token`。

### REQ-006 仿真倍速控制

- 新增 `set_simulation_speed`
- 参数：`simulation_id`、`speed`、可选 `record_id`
- 自动定位运行记录（可选）

**验收标准**
1. 可下发倍速控制请求。
2. 参数非法（如 `speed<=0`）时返回明确错误。

---

## 3. 工具与代码映射

| MCP工具 | 代码入口 | 说明 |
|---|---|---|
| `list_scenarios` | `src/server.py` | 查询想定，支持分页/全量/标签过滤 |
| `list_models` | `src/server.py` | 查询模型，支持关键词与模型案例过滤 |
| `control_scenario` | `src/server.py` | 控制想定生命周期 |
| `download_record_data` | `src/server.py` | 下载并解压运行记录 |
| `set_simulation_speed` | `src/server.py` | 设置仿真倍速 |

---

## 4. 运行与配置要求

### 4.1 环境变量

- `LAVIC_API_BASE_URL`
- `LAVIC_USER_ID`
- `LAVIC_API_TOKEN`

### 4.2 MCP 客户端配置（示例）

```json
{
  "mcpServers": {
    "lavic-control": {
      "command": "python",
      "args": [
        "/ABSOLUTE/PATH/TO/lavicmcp/src/server.py"
      ],
      "env": {
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

---

## 5. 当前版本说明

- 本文档是“与现有代码一致”的 Story1 版本。
- 需要增强的后续能力：
  - 控制动作的显式状态机校验
  - 下载自动重试策略
  - 独立分析模块与标准化报表
  - trace_id / 耗时 / 结果码等可观测性字段
