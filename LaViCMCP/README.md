# LaViC MCP Server

这是一个用于通过自然语言控制 LaViC 仿真系统的 MCP (Model Context Protocol) 服务器。

它允许您使用 AI 助手（如 Trae, Claude Desktop, Cursor）来：
- 查询和筛选想定案例
- 查询仿真模型
- 启动、暂停、恢复、停止想定运行
- 下载运行记录数据

## 目录结构

```text
LaViC-MCP/
├── src/
│   └── server.py          # 核心 MCP 服务器代码
├── scripts/               # 临时工具脚本和测试代码
├── .env.example           # 配置文件模板
├── requirements.txt       # Python 依赖包
└── README.md              # 本说明文档
```

## 快速开始

### 1. 环境准备

确保已安装 Python 3.10+。

```bash
# 克隆或下载本项目后，安装依赖
pip install -r requirements.txt
```

### 2. 配置文件

复制 `.env.example` 为 `.env`，并填入您的 LaViC 配置信息：

```bash
cp .env.example .env
```

在 `.env` 文件中填入：
- `LAVIC_API_BASE_URL`: LaViC Core API 地址
- `LAVIC_USER_ID`: 您的用户 ID
- `LAVIC_API_TOKEN`: 您的 API Token (admin-Token)

### 3. 在 MCP 客户端中使用

#### Claude Desktop / Trae 配置

在您的 MCP 配置文件中（通常是 `claude_desktop_config.json` 或 AI 助手的 MCP 设置），添加以下内容：

**注意：请将路径替换为您本地的实际绝对路径。**

```json
{
  "mcpServers": {
    "lavic-control": {
      "command": "python",
      "args": [
        "D:/Path/To/LaViC-MCP/src/server.py"
      ],
      "env": {
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

### 4. 功能列表

- **list_scenarios**: 列出想定案例（支持分页和 `fetch_all`）
- **list_models**: 列出仿真模型（支持关键词搜索、`is_model_case` 筛选）
- **control_scenario**: 控制想定（start, pause, resume, stop）
- **download_record_data**: 下载运行记录数据（自动解压 ZIP）

## 常见问题

- **数据不全？** 使用 `fetch_all=True` 参数可以让 AI 自动拉取所有分页数据。
- **无法连接？** 请检查 `.env` 中的 Token 是否过期，以及 API 地址是否可达。
