# GitHub 发布与协作指南

## 1. 首次发布到 GitHub

在项目目录执行：

```bash
git init
git add .
git commit -m "init: prd templates, agent, and prd-vibecoding skill"

git branch -M main
git remote add origin <你的仓库地址>
git push -u origin main
```

建议在仓库 Settings 中开启：

- Branch protection（保护 `main`）
- Pull request review（至少 1 人审核）
- Secrets scanning（防止 Token 泄露）

## 2. 协作者拉取后怎么用

```bash
git clone <你的仓库地址>
cd productPRD
```

### 方式A：直接用模板

- 编辑 `PRD_TEMPLATE.md`
- 编辑 `prd-lavic-mcp-story1.html` 或 `prd-prototype.html`

### 方式B：用对话 Agent 自动追问补全

```bash
python3 prd_agent.py chat
```

输出会写入：

- `generated/PRD_LIVE.md`
- `generated/prd-live.html`

## 3. 使用 prd-vibecoding Skill（推荐）

仓库里已提供 skill：

- `skills/prd-vibecoding/SKILL.md`

协作者把该目录复制到自己的 `$CODEX_HOME/skills` 下即可，例如：

```bash
mkdir -p "$CODEX_HOME/skills"
cp -R skills/prd-vibecoding "$CODEX_HOME/skills/"
```

之后在对话中显式调用：`$prd-vibecoding`。

## 4. 协作约定（强制）

1. 每个需求都必须有 `REQ-*` ID。
2. Markdown 与 HTML 必须同版本同步更新。
3. 缺失项必须写入 `Open Questions`，不得静默跳过。
4. 提交 PR 时附上：
   - 变更前后差异说明
   - 验收标准是否受影响
   - 涉及的图（流程/时序/架构/状态机）是否更新

## 4.1 Issue 提单规范

仓库已配置 `.github/ISSUE_TEMPLATE/`：

- `prd-feature-request.yml`：新需求提单（从必要性到 REQ、图、验收一并收集）
- `prd-change-request.yml`：已有 PRD 变更提单（强制填写影响的 `REQ-*` 和同步状态）

建议流程：先开 Issue -> 再建分支 -> 提交 PR -> CI 校验通过后合并。

## 5. 安全注意

- 不要提交 `.env`、token、内部地址。
- 对外分发包排除 `.env` 和 `__pycache__`。
