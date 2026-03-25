# Subagents 重构说明（完整版）

## 重构目标

- 将原本分散且多处 `pass` 的 `agents/*` 升级为可执行的 `subagents` 流水线。
- 让“生成想定”和“审计既有想定”走同一条状态流。
- 保留老入口兼容性，避免外部调用立即失效。

## 主架构

- `src/subagents/state.py`: 统一 state 定义与初始化。
- `src/subagents/base.py`: 子代理统一接口。
- `src/subagents/services/`: IO、审计、修复服务。
- `src/subagents/*_subagent.py`: 六个职责清晰的子代理实现。
- `src/core/subagent_orchestrator.py`: 串联全流程并负责失败状态收敛。
- `src/main.py`: CLI 入口（支持 `--input`、`--intent`、`--output-dir`、`--state-output`）。

## 老结构兼容

- `src/core/orchestration.py::Orchestrator` 仍可使用，内部转调 `SubAgentOrchestrator`。
- `src/agents/*` 的旧类接口改为包装器实现，不再是空方法。

## 迁移建议

1. 后续新增能力统一放在 `src/subagents/services/*` 与 `src/subagents/*_subagent.py`。
2. 避免在 `subagent` 中直接写文件/网络细节，通过 service 注入实现。
3. 保持 state 字段稳定，新增字段先在 `state.py` 声明。
4. 当 MCP 接口就绪后，仅替换 `OperatorSubAgent` 的执行实现，不改全局流程。
