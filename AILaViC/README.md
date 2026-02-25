# AILaViC

AILaViC 是一个基于 LLM 和多智能体的仿真想定编排系统，旨在通过自然语言生成高质量、可运行、逻辑自洽的仿真想定，并通过 MCP 协议在 LaViC 仿真平台上运行。

## 项目架构

- **Auditor First**: 优先实现审计功能，确保生成的想定符合物理、战术和资源完整性要求。
- **Core Engine**: 基于状态机 (LangGraph) 的智能体编排。
- **Agents**:
    - **KnowledgeAgent**: 检索和管理知识。
    - **CreatorAgent**: 生成战术想定。
    - **AuditorAgent**: 审计和检查想定。
    - **FixerAgent**: 修复审计发现的问题。
    - **OperatorAgent**: 执行仿真任务。
    - **DebuggerAgent**: 分析和复盘。

## 快速开始

1.  安装依赖: `pip install -r requirements.txt` (or use poetry/pdm)
2.  配置 `.env`
3.  运行: `python src/main.py`
