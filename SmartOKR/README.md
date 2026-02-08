# SmartOKR MCP Server

基于证据链的 OKR 绩效分析系统 —— 理性辅助裁判系统。

## 功能特性

- **GitHub + Get笔记知识库** 工作记录自动采集
- **平衡计分卡(BSC)** 四维度 OKR 管理
- **岗位动态权重** 不同岗位自动应用不同维度权重
- **AI 证据链推理** 将工作证据匹配到 OKR 关键成果
- **结构化报告** 生成 Markdown 格式绩效分析报告
- **可迭代补充** 每次评估可补充工作证据

## 快速开始

### 1. 安装依赖

```bash
cd SmartOKR
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env 填入 GitHub Token 和 Get笔记 API Key
```

### 3. 配置 MCP 客户端

将以下配置添加到 Claude Desktop / Trae / Cursor 的 MCP 配置中：

```json
{
  "mcpServers": {
    "smartokr": {
      "command": "python",
      "args": ["/absolute/path/to/SmartOKR/src/server.py"],
      "env": {"PYTHONUTF8": "1"}
    }
  }
}
```

### 4. 使用

通过 AI 助手调用 11 个 MCP 工具进行 OKR 管理。详见 [skill.md](skill.md)。

## 工具列表

| 类别 | 工具名 | 功能 |
|------|--------|------|
| OKR管理 | `create_okr_objective` | 创建目标（绑定BSC维度） |
| OKR管理 | `create_key_result` | 添加关键成果 |
| OKR管理 | `list_okrs` | 查询OKR树 |
| OKR管理 | `update_okr` | 更新目标/KR |
| 证据采集 | `collect_github_evidence` | GitHub commits/PRs/issues |
| 证据采集 | `collect_notes_evidence` | Get笔记知识库文档 |
| 证据采集 | `add_evidence_manually` | 手动补充证据 |
| 分析 | `match_evidence_to_okrs` | 证据匹配上下文 |
| 分析 | `store_evidence_matches` | 存储AI匹配结果 |
| 分析 | `calculate_scores` | BSC动态权重评分 |
| 报告 | `generate_report` | 生成绩效报告 |

## 岗位权重预设

| 岗位 | 财务 | 客户 | 内部流程 | 学习成长 |
|------|------|------|----------|----------|
| engineer | 10% | 20% | 45% | 25% |
| product_manager | 20% | 35% | 25% | 20% |
| sales | 40% | 30% | 15% | 15% |
| designer | 10% | 35% | 30% | 25% |
| manager | 25% | 25% | 30% | 20% |
| researcher | 10% | 15% | 35% | 40% |
| operations | 25% | 25% | 35% | 15% |

## 技术栈

- Python 3.10+
- MCP (Model Context Protocol)
- Get笔记 OpenAPI（知识库搜索与召回）
- GitHub API / gh CLI
- 本地 JSON 文件存储（无需数据库）

## 目录结构

```
SmartOKR/
├── src/
│   ├── server.py            # MCP 服务入口
│   ├── models.py            # 数据模型
│   ├── store.py             # JSON 持久化
│   ├── github_collector.py  # GitHub 采集
│   ├── notes_collector.py   # Get笔记采集
│   ├── scoring_engine.py    # 评分引擎
│   ├── report_generator.py  # 报告生成
│   └── utils.py             # 工具函数
├── data/                    # 运行时数据
├── skill.md                 # AI助手使用指南
├── .env.example             # 配置模板
└── requirements.txt         # 依赖
```
