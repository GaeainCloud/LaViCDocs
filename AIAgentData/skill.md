# Simulation Model Generation & Packaging Pipeline (NLP to ZIP)

## 1. 技能概述 (Overview)
本技能定义了从 **自然语言描述** 到最终 **LaViC 标准模型资产包 (.zip)** 的全自动化生成流水线。该流程不仅适用于无人机，也适用于车辆、船舶、导弹等其他仿真实体。

核心目标：**"One Prompt to Simulation Model"** —— 输入一段描述，输出一个可直接导入 LaViC 系统的标准 ZIP 包。

## 2. 标准流水线 (Pipeline Steps)

### 2.1 步骤一：模型定义与生成 (Definition & Generation)
- **输入**: 自然语言描述（例如：“一辆最大速度 80km/h 的装甲侦察车，配备光电传感器”）。
- **处理**:
  - **JSON 构建**: 基于 `src/AI生成AgentData代码参考/` 中的逻辑，利用 LLM 提取属性，构建 `AgentData.json`。
  - **Schema 校验**: 使用 `src/validator.py` 验证生成的 JSON 是否符合 `AgentData_schema.json`。
- **输出**: 基础 `agent.json` 文件。

### 2.2 步骤二：资产获取与生成 (Asset Acquisition)
根据模型类型自动准备三类核心资源：
1.  **缩略图 (Thumbnail)**:
    - 来源：Web Search (必须使用 Web Research Server MCP)。
    - 策略：**风格一致性与质量优选 (Style Consistency & Quality Selection)**。
      - **强制要求**：必须确保搜索到合适的图片，不得使用无效或低质量占位符。若 Web Research Server 返回结果不佳，需优化搜索词重新尝试。
      - 对每个模型搜索 3-5 张候选图片。
      - **风格标准 (Style Guidelines)**：
        - **优先风格**：**3D 渲染图 (3D Studio Render)** > **干净背景实拍图 (Clean Photo)** > **实拍图 (Real Photo)**。
        - **背景要求**：优先选择 **白色、灰色 (Studio Grey)** 或 **透明** 背景，避免复杂环境干扰。
        - **视角要求**：优先选择 **3/4 等轴侧视图 (Isometric/3/4 View)**，其次为 **正侧视图 (Side View)**。此视角最利于展示模型立体感及后续 3D 生成。
      - 优选标准：
        - 清晰度高：分辨率 > 800px (宽或高)。
        - 主体完整：车辆主体在图片中占比适中，无严重遮挡。
      - 自动化：脚本下载所有候选图，通过文件大小和分辨率算法自动择优（例如：优先选分辨率最大且文件体积适中的图片）。
    - 格式：PNG/JPG。
    - 命名：`{ModelName}.png`。
2.  **军标 (Military Symbol)**:
    - 工具：`src/gen_mil_symbols.py` (基于 `military-symbol` 库)。
    - 标准：NATO APP-6(D)。
    - 命名：`{ModelName}_mil.png`。
3.  **3D 模型 (3D Model)**:
    - 来源：Rodin (AI生成) / Blender / 现有库。
    - 格式：GLB。
    - 命名：`{ModelName}_AI_Rodin.glb`。

### 2.3 步骤三：资产标准化处理 (Asset Standardization)
**[严格执行]** 必须对 3D 模型进行几何修正，确保在 LaViC 场景 (Y-Up 坐标系) 中姿态正确。此步骤不可省略。

- **修正逻辑 (必须按顺序执行)**:
  1.  **坐标轴修正 (Z-Up -> Y-Up)**: 绕 X 轴旋转 **-90°**。
  2.  **朝向修正 (Facing Correction)**: 绕 Y 轴 (即新坐标系下的垂直轴) 旋转 **180°**。
  - **结果验证**: 模型应正立 (Y轴向上)，且机头/车头朝向正确 (通常对应 Y 轴旋转 180 度后的方向)。

- **实现方式**:
  - **Python (推荐)**: 使用 `trimesh` 库直接处理 GLB 文件 (参考 `src/fix_glb_rotation.py`)。
  - **Blender**: 使用 `bpy` 脚本处理。
  - **注意**: 若使用 `trimesh`，请确保先执行 X 轴旋转，再执行 Y 轴旋转。

### 2.4 步骤四：目录结构与配置 (Structure & Configuration)
- **目录规范**:
  ```text
  models/
  └── {ModelName}/            # 独立模型文件夹
      ├── agent.json          # 配置文件
      └── {ModelName}/        # 资源子文件夹
          ├── {ModelName}.png
          ├── {ModelName}_mil.png
          ├── {ModelName}_AI_Rodin.glb
  ```
- **配置修复 (Configuration Fixes)**:
  - 脚本：`src/fix_and_zip_models.py` 或生成脚本内部逻辑。
  - **[严格执行] 必须更新以下所有字段，严禁遗漏**:
    1.  **根级字段**: `agentName`, `modelUrlSlim`, `modelUrlFat`, `modelUrlSymbols`。
    2.  **嵌套 model 对象 (关键)**: 必须同步更新 `model` 对象内部的以下字段，**不可保留模板默认值**：
        - `model.modelName`: 必须与根级 `agentName` 一致。
        - `model.thumbnail`: 必须指向 `{ModelName}/{ModelName}.png`。
        - `model.mapIconUrl`: 必须指向 `{ModelName}/{ModelName}_mil.png`。
        - `model.dimModelUrls`: 必须指向 `{ModelName}/{ModelName}_AI_Rodin.glb`。
    - **路径格式**: 所有资源引用必须使用相对路径 `"{ModelName}/{Filename}"`。

### 2.5 步骤五：最终打包 (Final Packaging)
- **工具**: `src/zip_models.py` (被 `fix_and_zip_models.py` 调用)。
- **要求**:
  - **格式**: `.zip`。
  - **编码**: **UTF-8** (必须支持中文文件名)。
  - **结构**: **Flat Structure** (扁平化)。
    - 错误：ZIP -> `{ModelName}/` -> `agent.json`
    - 正确：ZIP -> `agent.json`, `{ModelName}/` (资源文件夹)
- **产物**: `models/{ModelName}.zip`。

## 3. 核心脚本工具箱 (Toolbox)

| 脚本文件 | 功能描述 | 关键依赖 |
| :--- | :--- | :--- |
| `src/validator.py` | 校验 `agent.json` 结构合法性 | `jsonschema` |
| `src/gen_mil_symbols.py` | 生成 APP-6D 标准军标 PNG | `military-symbol`, `reportlab` |
| `src/process_glbs.py` | 批量调整 GLB 坐标轴 (Y-Up) | `bpy` (Blender API) |
| `src/rotate_glbs_z180.py` | 批量调整 GLB 朝向 (Rotate 180) | `bpy` (Blender API) |
| `src/fix_and_zip_models.py` | 批量修复 JSON 路径并打包 | `src/zip_models.py` |
| `src/zip_models.py` | 创建 UTF-8 编码的扁平化 ZIP | `zipfile` |
| `src/generate_vehicle_packages.py` | 批量生成车辆模型包 (Orchestrator) | `pandas`, `military_symbol` |
| `src/fetch_images.py` | 自动获取参考图片 | `requests` |
| `src/check_and_convert_images.py` | 图片格式检查与转换 (RGB PNG) | `Pillow` |
| `src/blender_mcp_addon.py` | Blender MCP 插件 (Hyper3D 集成) | `bpy`, `requests` |

## 4. 扩展指南 (Extension Guide)
若要支持新类型的模型（如“潜艇”）：
1.  **JSON 生成**: 确保 `agentType` 和 `dynamics` 选择正确（如 `HydroDynamics`）。
2.  **军标生成**: 在 `gen_mil_symbols.py` 中添加对应的 SIDC 代码映射。
3.  **3D 模型**: 获取潜艇 GLB 模型，并运行 Blender 脚本修正坐标。
4.  **执行打包**: 运行 `python src/fix_and_zip_models.py` 即可自动完成修复与打包。
