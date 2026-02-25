---
name: "ailavic-builder"
description: "自动构建和管理 AILaViC 项目结构，包括智能体 (Agents)、核心引擎 (Core Engine) 和仿真层 (Simulation Layer)。在设置或扩展 AILaViC 组件时调用此技能。"
---

# AILaViC 构建助手 (AILaViC Builder)

本技能旨在协助系统化构建和维护 AILaViC 项目。它封装了“审计优先 (Auditor First)”的开发策略和模块化智能体架构。

## 核心能力 (Capabilities)

### 1. 项目初始化 (Project Initialization)
- **功能**: 搭建整个项目的目录骨架。
- **用法**: "初始化 AILaViC 项目结构" (Initialize the AILaViC project structure)
- **组件**:
    - 根配置 (`.env`, `pyproject.toml`, `docker-compose.yml`)
    - 源代码目录 (`src/core`, `src/agents`, `src/schemas`, `src/simulation`)
    - 基础设施 (`knowledge_base`, `tests`, `logs`)

### 2. 智能体构建 (Agent Construction)
- **功能**: 基于标准模板生成特定智能体的样板代码。
- **用法**: "创建 [AgentName] 智能体" (Create the [AgentName] agent)
- **模板**:
    - `__init__.py`: 模块导出
    - `manager.py`: 主智能体逻辑/入口点
    - `tools.py` / `probes.py`: 智能体特定能力

### 3. 仿真层管理 (Simulation Layer Management)
- **功能**: 管理仿真引擎 (C++) 和 Python 动力学模块的集成。
- **用法**: "更新仿真层" (Update simulation layer) 或 "集成新动力学模型" (Integrate new dynamics model)
- **结构**:
    - `src/simulation/event_engine`: 基于 Python 的离散事件引擎
    - `src/simulation/dynamics`: Python 运动学和 C++ 绑定
    - `src/simulation/GaeactorEngineDynaModex`: C++ 核心引擎

### 4. 数据模型与协议管理 (Schema & Protocol Management)
- **功能**: 更新数据模型和协议定义。
- **用法**: "从 proto 文件更新 schemas" (Update schemas from proto files) 或 "同步智能体数据模型" (Sync agent data models)
- **目标**: `src/schemas/lavic_proto`, `src/schemas/agent_data.py`

## 最佳实践 (Best Practices)
- 始终遵循 **审计优先 (Auditor First)** 策略：在实现生成逻辑 (Creator) 之前，先实现验证逻辑 (Auditor)。
- 使用 **Proto3** 作为引擎数据结构的单一事实来源 (Source of Truth)。
- 确保所有新智能体都继承自 `src.agents.base_agent.BaseAgent`。
