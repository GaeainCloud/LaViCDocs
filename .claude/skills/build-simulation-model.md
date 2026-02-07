# Skill: build-simulation-model

## Description
仿真模型构建 - 从自然语言描述到 LaViC 标准仿真模型资产包 (.zip) 的全自动化生成流水线。

## Invocation
当用户请求构建仿真模型时触发，例如：
- "帮我构建一个 F-22 战斗机的仿真模型"
- "创建一辆装甲侦察车的模型包"
- "生成无人机仿真模型"
- "/build-simulation-model"

## Instructions

你是 LaViC 仿真模型构建专家。当用户提供自然语言描述时，按照以下 5 步流水线生成标准模型资产包。

### 前置准备

在开始之前，必须：
1. 阅读并理解 `AIAgentData/skill.md` 中的完整流水线定义
2. 确认用户描述中包含的模型类型（车辆/飞机/船舶/导弹/eVTOL/无人机等）
3. 向用户确认模型名称（英文，用于文件命名）和中文显示名

### 步骤一：模型定义与生成 (Definition & Generation)

**输入**: 用户的自然语言描述
**处理**:
1. 根据描述识别模型类型，选择最匹配的模板文件：
   - 车辆: `AIAgentData/examples/01vehicleAgent.json`
   - 飞机: `AIAgentData/examples/02aircraftAgent.json`
   - eVTOL: `AIAgentData/examples/03evtolAgent.json`
   - 水下载具: `AIAgentData/examples/04underwaterVehicleAgent.json`
   - 船舶: `AIAgentData/examples/05shipAgent.json`
   - 巡飞弹: `AIAgentData/examples/06loiterMunitionAgent.json`
   - 导弹: `AIAgentData/examples/07missileAgent.json`

2. 基于模板生成 `agent.json`，必须填充以下字段：
   - `agentName`: 模型中文名
   - `agentNameI18n`: 同 agentName
   - `agentKeyword`: 模型拼音缩写（小写）
   - `agentDesc`: 简短描述
   - `agentType`: "Instagent"
   - `agentCamp`: 根据阵营选择（默认红方）
   - `missionable`: true
   - `missionableDynamics`: 根据类型选择动力学插件
     - 车辆: `iagnt_dynamics_vehicle_simple`
     - 飞机: `iagnt_dynamics_carrier_based_aircraft`
   - `model`: 资产引用对象（步骤四中填充）
   - `waypoints`: 至少包含一条默认路径

3. 使用 Schema 校验：
   ```bash
   python AIAgentData/src/validator.py --schema AIAgentData/src/校验代码参考/AgentData_schema.json --data <生成的agent.json路径>
   ```

**输出**: `models/{ModelName}/agent.json`

### 步骤二：资产获取与生成 (Asset Acquisition)

为每个模型准备三类核心资源：

#### 2.1 缩略图 (Thumbnail)
- **来源**: 使用 Web Search 工具搜索参考图片
- **搜索策略**:
  - 搜索词示例: "{模型名} 3D render white background", "{模型名} isometric view"
  - 搜索 3-5 张候选图
  - **风格优先级**: 3D 渲染图 > 干净背景实拍图 > 实拍图
  - **背景要求**: 白色/灰色/透明背景优先
  - **视角要求**: 3/4 等轴侧视图优先
  - **质量要求**: 分辨率 > 800px
- **下载处理**: 使用 `AIAgentData/src/fetch_images.py` 或手动下载
- **格式转换**: 使用 `AIAgentData/src/check_and_convert_images.py` 确保为 RGB PNG
- **命名**: `{ModelName}.png`

#### 2.2 军标 (Military Symbol)
- **标准**: NATO APP-6(D)
- **工具**: `AIAgentData/src/gen_mil_symbols.py`
- **依赖**: `military-symbol`, `svglib`, `reportlab`
- **流程**:
  1. 确定正确的 SIDC 描述字符串（如 "Friendly Fixed Wing Aircraft"）
  2. 调用 `military_symbol.get_symbol_svg_string_from_name()` 生成 SVG
  3. 使用 `svglib` + `reportlab` 转换为 PNG
- **命名**: `{ModelName}_mil.png`

#### 2.3 3D 模型 (3D Model)
- **来源**: Rodin AI 生成 / Blender / 现有库
- **格式**: GLB
- **命名**: `{ModelName}_AI_Rodin.glb`
- **注意**: 如果环境中无法生成 3D 模型，告知用户需要手动提供或使用 Rodin API

### 步骤三：资产标准化处理 (Asset Standardization)

**[严格执行]** 对 3D 模型进行坐标修正：

```python
import trimesh
import numpy as np

scene = trimesh.load(glb_path, force='scene')

# 1. Z-Up -> Y-Up: 绕 X 轴旋转 -90 度
rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
scene.apply_transform(rot_x)

# 2. 朝向修正: 绕 Y 轴旋转 180 度
rot_y = trimesh.transformations.rotation_matrix(np.radians(180), [0, 1, 0])
scene.apply_transform(rot_y)

# 导出
data = trimesh.exchange.gltf.export_glb(scene)
with open(output_path, 'wb') as f:
    f.write(data)
```

参考脚本: `AIAgentData/src/fix_glb_rotation.py`

### 步骤四：目录结构与配置 (Structure & Configuration)

#### 4.1 创建标准目录
```
models/{ModelName}/
├── agent.json
└── {ModelName}/
    ├── {ModelName}.png
    ├── {ModelName}_mil.png
    └── {ModelName}_AI_Rodin.glb
```

#### 4.2 更新 agent.json 资产引用

**[严格执行] 必须更新以下所有字段，不可保留模板默认值：**

```python
agent_data = {
    # ... 其他字段 ...

    # 根级字段
    "agentName": "{中文模型名}",
    "modelUrlSlim": "{ModelName}/{ModelName}_AI_Rodin.glb",
    "modelUrlFat": "{ModelName}/{ModelName}_AI_Rodin.glb",
    "modelUrlSymbols": [
        {
            "symbolSeries": 1,
            "symbolName": "{ModelName}/{ModelName}.png",
            "thumbnail": "{ModelName}/{ModelName}.png"
        },
        {
            "symbolSeries": 2,
            "symbolName": "{ModelName}/{ModelName}_mil.png",
            "thumbnail": "{ModelName}/{ModelName}_mil.png"
        }
    ],

    # model 嵌套对象 (关键！)
    "model": {
        "modelName": "{中文模型名}",
        "thumbnail": {
            "url": "{ModelName}/{ModelName}.png",
            "selected": False,
            "bucket": "lavic",
            "ossSig": "{ModelName}.png"
        },
        "mapIconUrl": {
            "url": "{ModelName}/{ModelName}_mil.png",
            "selected": False,
            "bucket": "lavic",
            "ossSig": "{ModelName}_mil.png"
        },
        "dimModelUrls": [{
            "url": "{ModelName}/{ModelName}_AI_Rodin.glb",
            "selected": True,
            "bucket": "lavic",
            "ossSig": "{ModelName}_AI_Rodin.glb"
        }]
    }
}
```

参考脚本: `AIAgentData/src/fix_and_zip_models.py`

### 步骤五：最终打包 (Final Packaging)

```python
import zipfile
import os

def zip_model(model_dir, output_zip):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(model_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # 扁平化结构：相对于 model_dir
                rel_path = os.path.relpath(file_path, model_dir)
                zipf.write(file_path, arcname=rel_path)
```

**打包要求**:
- **编码**: UTF-8（支持中文文件名）
- **结构**: 扁平化 —— ZIP 根目录直接包含 `agent.json` 和 `{ModelName}/` 资源文件夹
  - 正确: `ZIP -> agent.json + {ModelName}/`
  - 错误: `ZIP -> {ModelName}/ -> agent.json`
- **输出**: `models/{ModelName}.zip`

参考脚本: `AIAgentData/src/zip_models.py`

### 完成后校验清单

- [ ] `agent.json` 通过 Schema 校验
- [ ] 所有资产文件存在且命名正确
- [ ] 3D 模型已完成坐标轴修正（Y-Up，朝向正确）
- [ ] `agent.json` 中所有路径引用已更新（无模板默认值残留）
- [ ] `model` 对象内的 `modelName`、`thumbnail`、`mapIconUrl`、`dimModelUrls` 均已更新
- [ ] ZIP 包为扁平结构，UTF-8 编码
- [ ] 缩略图为 RGB PNG 格式，分辨率 > 800px

### 关键参考文件

| 文件 | 用途 |
|------|------|
| `AIAgentData/skill.md` | 完整流水线定义 |
| `AIAgentData/src/校验代码参考/AgentData_schema.json` | JSON Schema |
| `AIAgentData/src/validator.py` | Schema 校验工具 |
| `AIAgentData/src/gen_mil_symbols.py` | 军标生成 |
| `AIAgentData/src/fix_glb_rotation.py` | GLB 坐标修正 |
| `AIAgentData/src/fix_and_zip_models.py` | JSON 路径修复 + 打包 |
| `AIAgentData/src/zip_models.py` | ZIP 打包 |
| `AIAgentData/src/check_and_convert_images.py` | 图片格式转换 |
| `AIAgentData/src/fetch_images.py` | 图片下载 |
| `AIAgentData/examples/` | 各类型模板 (01-30) |

### 扩展指南

若要支持新类型的模型（如"潜艇"）：
1. **JSON 生成**: 确保 `agentType` 和 `dynamics` 选择正确（如 `HydroDynamics`）
2. **军标生成**: 在配置中添加对应的 SIDC 描述映射
3. **3D 模型**: 获取 GLB 模型并运行坐标修正
4. **执行打包**: 运行修复和打包脚本
