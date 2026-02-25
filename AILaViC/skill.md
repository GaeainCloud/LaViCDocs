# AILaViC 技能与工作流

## 想定审计与修复工作流（人工修复模式）

本工作流描述了对现有想定包（Zip）进行审计、分析物理合规性、人工修复问题并重新打包为新版本的全过程。

### 1. 物理合规性审计
**目标**: 识别想定中违反物理公理（运动学、空间、能源、时序）的问题。

**流程**:
1.  **输入**: 现有的想定 Zip 包（例如 `Scenario_v1.zip`）。
2.  **工具执行**: 运行 Auditor 智能体或脚本（例如 `run_audit.py`）。
    - Auditor 解压 Zip 并分析 `simulation.json`。
    - 检查四大公理：运动学一致性、空间排他性、能源守恒、因果时序性。
3.  **分析输出**:
    - **红灯（严重）**: 物理违规（例如：速度 > 最大速度，瞬间移动）。
    - **黄灯（警告）**: 战术或逻辑不一致。
    - **定位器**: 提供具体的行号或 JSON 路径（例如 `agentInstances[0].waypoints[1]`）。

**输出格式要求**:
物理检测约束后要生成的报告结果必须是格式化的，并生成Markdown文档。
1. **序号**: 必须是递增的数字序号（1, 2, 3...）。
2. **实体标识**: 必须包含 `instanceName` 和 `agentName`，格式如 `instanceName (agentName)`。
3. **检查项详单**: 不仅仅列出最大速度，必须列出系统规则中定义的每一项约束（如速度、过载、高度、航程、续航等）的检测值与阈值对比。
4. **Markdown文档**: 最终必须生成一个 `physics_check_report.md` 文档。

### 2. 人工分析与修复策略
**目标**: 确定如何解决识别出的红灯问题。

**常见修复策略**:
- **超速（距离/时间不匹配）**:
    - *方法 A (调整时间)*: 保持坐标不变，增加时间段 ($T$) 以降低速度。
        - 公式: $T_{new} \ge Distance / V_{max}$
    - *方法 B (调整坐标)*: 保持时间不变，移动航路点使其距离更近以减少路程。

### 3. 执行：修复与打包
**目标**: 应用修复并生成干净、有效的发布包。

**步骤**:
1.  **创建修复文件夹**:
    - 以目标版本命名创建一个新目录（例如 `Scenario_v2-Fixed`）。
    - 从源包中复制所有内容（图片、模型等）到这个新文件夹。

2.  **应用修复 (修改 JSON)**:
    - 在新文件夹中打开 `simulation.json`。
    - 根据审计报告定位有问题的实体/航路点。
    - 应用计算出的数值（例如更新 `wpsCore` 的时间索引）。
    - **关键**: 如果 `simulation.json` 中的内部文件路径引用了旧文件夹名称，必须更新这些路径（例如将 `OldName/Asset.png` 替换为 `NewName/Asset.png` 或相对路径）。

3.  **验证与 Schema 校验**:
    - **Schema 检查**: `simulation.json` **必须** 通过 `src/schemas/` 下 4 个核心 Schema 的校验：
        - `AgentData_schema.json`
        - `doctrine_schema.json`
        - `doe.schema.json`
        - `patterndata_schema.json`
    - **资源检查**: 验证 JSON 中的资源路径是否指向新文件夹结构中存在的实际文件。
    - **规则**: 只有当 *所有* 校验通过时，才允许进行打包。

4.  **压缩 (扁平化打包 & UTF-8)**:
    - 将文件夹内容打包成 Zip 文件。
    - **编码**: Zip 归档 **必须** 使用 **UTF-8** 编码（例如 Python `zipfile` 默认支持，但若使用其他工具需确保显式处理）。
    - **结构**: Zip 根目录必须直接包含 `simulation.json` 和资源文件夹。**不要** 将它们包裹在顶层父文件夹中。
    - *正确结构*:
      ```text
      Scenario_v2.zip
      ├── simulation.json
      └── ScenarioName/
          ├── Asset1.png
          └── ...
      ```

### 5. 实体类型识别技巧
- **AgentName 与 InstanceName**: 
  - `instanceName` 是场景中该实体的唯一标识符（例如 "Bustling Buzzard"）。
  - `agentName` 是该实体对应的模板/类名称（例如 "DDG-51 Flight IIA" 或 "DF-15"）。
  - 当不确定实体的物理特性（如最大速度、类型）时，**必须** 检查 `agentName`。它通常直接对应具体的装备型号，从而可以查阅其真实性能参数。
  - **规则**: `instanceName` 仅用于区分个体，`agentName` 定义物理本质。

### 6. 脚本参考示例
(用于自动化的 Python 代码片段)

```python
# 计算半正矢距离 (Haversine Distance) 用于时间调整
import math
def haversine(lat1, lon1, lat2, lon2):
    # ... (标准公式) ...
    return distance

# 打包 Zip (扁平化结构)
import zipfile, os
with zipfile.ZipFile('output.zip', 'w') as z:
    for root, _, files in os.walk(src_dir):
        for f in files:
            # relpath 确保 zip 中没有顶层文件夹
            arcname = os.path.relpath(os.path.join(root, f), src_dir)
            z.write(os.path.join(root, f), arcname)
```
