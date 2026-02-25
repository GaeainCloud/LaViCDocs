# LaViC MCP Server

用于通过 MCP 协议控制 LaViC 仿真系统，支持查询、控制、数据下载与倍速调整。

## 功能

- `list_scenarios`: 查询想定（分页、`fetch_all`，默认 `simulationTag=1`）
- `list_models`: 查询模型（关键词、模型案例过滤、`fetch_all`）
- `control_scenario`: 想定控制（`start/pause/resume/stop`）
- `set_simulation_speed`: 设置运行中的仿真倍速
- `download_record_data`: 下载并解压运行记录 ZIP

## 运行要求

- Python 3.10+
- 与 LaViC 服务在同一局域网（LAN）或可路由互通网络
- 有效的 `LAVIC_USER_ID` 和 `LAVIC_API_TOKEN`

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 创建配置

```bash
cp .env.example .env
```

`.env` 必填：
- `LAVIC_USER_ID`
- `LAVIC_API_TOKEN`

`LAVIC_API_BASE_URL` 默认固定为：
`http://192.168.31.218:7980/api/v1/lavic-core`  
通常无需填写；仅在地址变更时覆盖该值。

3. 运行连通性自检

```bash
python scripts/self_check.py
```

返回 `[RESULT] Self-check passed.` 表示配置与接口连通正常。

4. 配置 MCP 客户端

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

## 工程规范说明

- 启动时会校验必要环境变量，缺失则直接报错退出。
- 网络请求具备超时控制，下载接口包含重试。
- `fetch_all` 分页拉取过程中遇错会返回错误与已拉取数量，不再静默返回部分结果。
- `.gitignore` 默认排除 `.env`、`__pycache__`、`.venv` 与数据目录。

## 常见问题

- `No running record found`：目标想定当前不在运行，先 `start` 或显式传 `record_id`。
- 下载返回 `400`：该记录可能没有可导出结果（常见于 `Unstart` 或刚启动即停止）。
