# AILaViC

AILaViC 是一个面向 LaViC 的仿真想定构建与审计项目。  
当前版本已按 `subagents` 结构重构：以子代理流水线为主架构，兼容旧 `agents` 接口。

## Subagents 架构

- 编排器: `src/core/subagent_orchestrator.py`
- 状态模型: `src/subagents/state.py`
- 子代理:
  - `KnowledgeSubAgent`: 识别模式（生成/审计）和领域提示
  - `CreatorSubAgent`: 从意图生成草案，或从 `zip/json/目录` 加载既有想定
  - `AuditorSubAgent`: 复用 `physics/logic/tactics/complexity/script` 探针执行审计
  - `FixerSubAgent`: 自动修复常见结构问题并复审
  - `OperatorSubAgent`: 产出 `scenario.generated.json` 和 `audit.report.json`
  - `DebuggerSubAgent`: 汇总运行诊断
- 服务层:
  - `src/subagents/services/io_service.py`
  - `src/subagents/services/audit_service.py`
  - `src/subagents/services/fix_service.py`
- 兼容层:
  - `src/core/orchestration.py` 保留 `Orchestrator`（转发到新编排器）
  - `src/agents/*` 原空实现已改为可用包装器

## 快速开始

1. 运行意图生成模式：

```bash
python src/main.py --intent "构建一个防空反导演练想定"
```

2. 运行既有想定审计模式（zip/json/目录都可以）：

```bash
python src/main.py \
  --input "knowledge_base/examples/想定_防空反导-v1.60.9-修复版.zip" \
  --intent "审计并修复防空反导想定" \
  --output-dir outputs/ad_audit
```

3. 保存最终状态：

```bash
python src/main.py --intent "构建联合演练想定" --state-output outputs/final_state.json
```
