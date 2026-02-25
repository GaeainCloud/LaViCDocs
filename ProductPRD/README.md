# PRD 资产包（可直接使用）

## 文件说明

- `PRD_TEMPLATE.md`：标准 PRD 模板（含 AI 专项、图示模板、需求追踪矩阵）。
- `prd-prototype.html`：可交互原型（支持流程切换、状态切换、需求 ID 追踪）。
- `prd-lavic-mcp-story1.html`：流程图看板版 HTML（流程图/架构图/时序图/状态机）。
- `skills/prd-vibecoding/`：可分发的 Skill，统一 MD + HTML 产出规范。
- `GITHUB_COLLAB_GUIDE.md`：GitHub 发布与团队协作操作手册。
- `scripts/validate_prd_assets.py`：PRD 规范校验脚本（用于 CI）。
- `.github/workflows/prd-lint.yml`：PR 提交自动校验流程。
- `.github/ISSUE_TEMPLATE/`：团队提需求与变更的标准 Issue 模板。

## 快速开始

1. 打开 `PRD_TEMPLATE.md`，先填写：文档信息、目标指标、In/Out Scope。
2. 将你的真实需求替换 `REQ-001/002/003`，保持 ID 全局唯一。
3. 打开 `prd-prototype.html`，在 `pages` 数组中替换页面与规则内容。
4. 评审时使用 HTML 演示交互，再用 Markdown 做条款确认和归档。

## Agent 化使用（口述需求自动整理）

### 启动

```bash
python3 prd_agent.py chat
```

### 会得到什么

- `generated/prd_state.json`：结构化状态（持续累积）
- `generated/PRD_LIVE.md`：自动更新的 PRD 文档
- `generated/prd-live.html`：自动更新的交互原型

### 对话行为

- 你可以随口说需求，Agent 会尝试自动抽取并写入文档。
- 对必填项缺失，Agent 会持续追问，直到补全。
- 每轮输入后都会实时更新 Markdown 和 HTML。

### 命令

```bash
python3 prd_agent.py status   # 查看当前缺失项
python3 prd_agent.py render   # 按当前 state 重新渲染
python3 prd_agent.py reset    # 重置并重新开始
```

### 可选：启用更强抽取（OpenAI API）

```bash
export OPENAI_API_KEY=你的key
python3 prd_agent.py chat
```

未设置 `OPENAI_API_KEY` 时，仍可使用规则抽取 + 追问填表模式。

## 推荐协作方式

- PM：维护目标、规则、验收、优先级。
- 设计：补齐视觉稿并映射到 `REQ-*`。
- 研发：按 `REQ-*` 建立任务与接口实现。
- 测试：按验收标准写用例并回填结果。
- 数据：按埋点表配置分析看板。

## AI 时代补充

- 每条需求都要有：失败定义 + 兜底动作。
- 模型指标与业务指标分开追踪。
- 默认提供降级方案，确保 AI 不可用时核心流程可运行。

## Skill 快速启用

```bash
mkdir -p "$CODEX_HOME/skills"
cp -R skills/prd-vibecoding "$CODEX_HOME/skills/"
```

在对话中使用：`$prd-vibecoding`

## CI 校验

```bash
python3 scripts/validate_prd_assets.py \
  --md PRD_LaViC_MCP_Story1.md \
  --html prd-lavic-mcp-story1.html
```

## Issue 模板协作

- 新功能需求：使用 `PRD Feature Request` 模板
- 现有文档变更：使用 `PRD Change Request` 模板
- 模板位置：`.github/ISSUE_TEMPLATE/`
