# SmartOKR Skill — 基于证据链的 OKR 绩效分析

## 1. 概述

SmartOKR 是一套 MCP 工具集，实现**基于证据链的 OKR 绩效分析**。它对接 GitHub 和 Get笔记知识库，自动采集工作记录，通过 AI 推理将证据匹配到 OKR 关键成果，并使用平衡计分卡(BSC)框架生成结构化绩效报告。

**核心理念**：「理性辅助裁判系统」—— 提供基于证据的分析，而非最终判断。

---

## 2. 标准工作流（6步 Pipeline）

```
┌─────────────┐   ┌──────────────┐   ┌──────────────┐
│  Step 1      │   │  Step 2       │   │  Step 3       │
│  OKR 设定    │──>│  证据采集     │──>│  证据匹配     │
│  (目标+KR)   │   │  (GitHub+笔记)│   │  (AI推理)     │
└─────────────┘   └──────────────┘   └──────────────┘
                                            │
┌─────────────┐   ┌──────────────┐          │
│  Step 6      │   │  Step 5       │   ┌─────▼────────┐
│  迭代补充    │<──│  报告生成     │<──│  Step 4       │
│  (补充证据)  │   │  (Markdown)   │   │  评分计算     │
└─────────────┘   └──────────────┘   └──────────────┘
```

### Step 1: OKR 设定

使用 `create_okr_objective` 创建目标，绑定 BSC 维度和负责人。然后用 `create_key_result` 为每个目标添加可衡量的关键成果。

```
示例对话：
用户: "为张伟设定 2025 Q1 的 OKR"

AI 调用:
1. create_okr_objective(title="提升平台可靠性", bsc_dimension="internal_process",
                        period="2025-Q1", owner="zhang_wei", weight=0.4)
   -> 返回 objective_id

2. create_key_result(objective_id="obj-xxx", title="P0事故降至2次以内",
                     target_value=2, unit="count", weight=0.5)
   -> 返回 kr_id
```

### Step 2: 证据采集

从 GitHub 和 Get笔记知识库自动采集工作记录，也可手动补充。

```
AI 调用:
1. collect_github_evidence(github_owner="OrgName", github_repo="repo",
                          author="zhangwei", since="2025-01-01", until="2025-03-31")
   -> 采集 commits、PRs、issues

2. collect_notes_evidence(person="zhang_wei",
                         queries=["张伟的项目进展", "张伟的技术方案"])
   -> 从知识库召回相关文档

3. add_evidence_manually(person="zhang_wei", title="主持架构评审会",
                        description="...", source_type="meeting", date="2025-02-15")
   -> 手动补充无法自动采集的证据
```

### Step 3: 证据匹配（AI 推理）

这是 SmartOKR 的核心——AI 作为「理性辅助裁判」进行证据链推理。

```
AI 调用:
1. match_evidence_to_okrs(person="zhang_wei", period="2025-Q1")
   -> 返回未匹配证据 + KR 定义列表

2. AI 逐条分析证据与 KR 的关联：
   "commit '修复事件循环内存泄漏' 直接关联 KR '降低P0事故'，
    因为内存泄漏是已知的P0事故根因..."

3. store_evidence_matches(matches=[
     {evidence_id: "ev-xxx", kr_id: "kr-xxx",
      relevance_score: 85,
      reasoning: "该提交修复了导致P0事故的内存泄漏...",
      contribution_type: "direct"}
   ])
```

### Step 4: 评分计算

使用动态权重引擎，**根据岗位自动应用不同的 BSC 维度权重**。

```
AI 调用:
calculate_scores(person="zhang_wei", period="2025-Q1", role="engineer")
-> 自动应用工程师权重: 财务10% | 客户20% | 内部流程45% | 学习成长25%
-> 返回各维度得分 + 综合得分
```

### Step 5: 报告生成

```
AI 调用:
generate_report(person="zhang_wei", period="2025-Q1",
               report_type="individual", output_format="markdown")
-> 生成完整的 Markdown 绩效分析报告
```

### Step 6: 迭代补充

每次评估都可以补充新的证据，重新计算得分和生成报告。

---

## 3. 工具参考（11个工具）

### OKR 管理

| 工具 | 用途 | 必填参数 |
|------|------|----------|
| `create_okr_objective` | 创建目标 | title, bsc_dimension, period, owner |
| `create_key_result` | 添加关键成果 | objective_id, title, target_value, unit |
| `list_okrs` | 查询 OKR 树 | (均可选: period, owner, bsc_dimension) |
| `update_okr` | 更新目标/KR | updates + (objective_id 或 kr_id) |

### 证据采集

| 工具 | 用途 | 必填参数 |
|------|------|----------|
| `collect_github_evidence` | GitHub 采集 | github_owner, github_repo, author, since, until |
| `collect_notes_evidence` | Get笔记采集 | person |
| `add_evidence_manually` | 手动补充 | person, title, description, source_type, date |

### 分析评分

| 工具 | 用途 | 必填参数 |
|------|------|----------|
| `match_evidence_to_okrs` | 获取匹配上下文 | person, period |
| `store_evidence_matches` | 存储匹配结果 | matches[] |
| `calculate_scores` | 动态权重评分 | person, period |

### 报告

| 工具 | 用途 | 必填参数 |
|------|------|----------|
| `generate_report` | 生成绩效报告 | person, period |

---

## 4. BSC 四维度指南

| 维度 | 英文 | 典型指标示例 |
|------|------|------------|
| **财务** | Financial | 营收增长、成本节约、ROI |
| **客户** | Customer | 满意度、留存率、NPS、需求响应速度 |
| **内部流程** | Internal Process | 系统可靠性、交付效率、代码质量、事故率 |
| **学习与成长** | Learning & Growth | 技能提升、知识分享、创新贡献、培训 |

---

## 5. 岗位动态权重

不同岗位的四维度权重分配不同，反映岗位职责差异：

| 岗位 | 财务 | 客户 | 内部流程 | 学习成长 |
|------|------|------|----------|----------|
| **engineer** 工程师 | 10% | 20% | **45%** | 25% |
| **product_manager** 产品经理 | 20% | **35%** | 25% | 20% |
| **sales** 销售 | **40%** | 30% | 15% | 15% |
| **designer** 设计师 | 10% | **35%** | 30% | 25% |
| **manager** 管理者 | 25% | 25% | **30%** | 20% |
| **researcher** 研究员 | 10% | 15% | 35% | **40%** |
| **operations** 运营 | 25% | 25% | **35%** | 15% |

也支持通过 `dimension_weights` 参数自定义权重。

---

## 6. 评分公式

```
KR 得分 = 完成度% × 0.7 + 证据强度 × 0.3
  ├── 完成度 = current_value / target_value × 100（上限100%）
  └── 证据强度 = 关联证据的 relevance_score 均值

目标得分 = Σ(KR得分 × KR权重) / Σ(KR权重)
维度得分 = Σ(目标得分 × 目标权重) / Σ(目标权重)
综合得分 = Σ(维度得分 × 维度权重)
```

---

## 7. 数据源配置

### GitHub
- 优先使用 `gh` CLI（自动认证、分页）
- 无 `gh` 时回退到 GitHub REST API（需配置 `GITHUB_TOKEN`）

### Get笔记知识库
- API: `https://open-api.biji.com/getnote/openapi`
- 认证: Bearer Token (`GETNOTE_API_KEY`)
- 知识库ID: `GETNOTE_TOPIC_ID`
- 支持两种模式：
  - `search` — AI 问答搜索
  - `recall` — 原始文档召回（用于证据采集）

---

## 8. 报告结构

生成的绩效报告包含：

1. **概览** — 综合得分、最强/最弱维度
2. **平衡计分卡概览** — 四维度得分表格
3. **各维度详细分析** — 每个目标和KR的得分明细
4. **进度与工作量分析** — 完成度、时间分布、工作量统计
5. **风险目标** — 完成度 < 50% 的目标预警
6. **声明** — "基于证据分析，仅供参考，不代表最终评价"
