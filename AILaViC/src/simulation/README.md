# Simulation Layer

该目录包含 AILaViC 的仿真与计算核心。

## 目录结构

- **GaeactorEngineDynaModex/**: LaViC 的 C++ 仿真引擎核心源码 (离散事件引擎 + 动力学)。
  - 包含 SGP4 轨道模型、RCS 计算、通信模型等底层实现。
  - 需要通过 CMake/Qt 编译。

- **dynamics/**: Python 动力学计算模块。
  - 目前提供基于 Python 的轻量级运动学计算 (Kinematics)，用于 Auditor 的快速审计。
  - 未来可扩展为调用 GaeactorEngineDynaModex 的 Python Bindings。

- **event_engine/**: Python 离散事件仿真接口。
  - 提供基础的时间轴 (Timeline) 和事件队列管理。
  - 用于验证想定的逻辑因果关系。

## 集成说明

AuditorAgent 在进行审计时，优先使用 `dynamics/` 和 `event_engine/` 中的 Python 实现进行快速校验。对于需要高精度物理验证的场景，未来将通过共享库接口调用 `GaeactorEngineDynaModex` 的编译产物。
