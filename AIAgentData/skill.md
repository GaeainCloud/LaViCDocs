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

- **客户端最终验收标准 (必须执行)**:
  - 上述标准化步骤只是默认起点，最终是否正确必须以 **LaViC 客户端中的坐标显示效果** 为准。
  - 对于飞机类模型，最终验收姿态统一定义为：
    - **机头朝向 `+X`**
    - **机背朝向 `+Z`**（不能翻肚皮）
    - **左右机翼沿 `Y` 轴展开**
  - 若模型在客户端中出现以下问题，按下面规则修正：
    - **机头朝 `-X`**: 绕 `Z` 轴旋转 `180°`
    - **翻肚皮，但机头方向正确**: 绕 `X` 轴旋转 `180°`
    - **机头朝反且翻肚皮**: 优先组合修正到“机头 `+X`、机背 `+Z`”，不要机械重复套用默认流程
  - **经验结论（Y-20 / BlenderMCP + Rodin）**:
    - 使用 BlenderMCP / Hyper3D Rodin 生成飞机模型后，默认导入姿态经常仍需一次 **客户端侧人工验收**。
    - 这类模型不要只依赖“X -90° + Y 180°”作为最终结论，必须在客户端中确认机头朝向与机背朝向。
  - **研发补充规则（Blender -> LaViC / three.js，强制执行）**:
    - **飞机类模型必须执行这条链路**，不能再按旧经验自由组合 Blender 侧预旋转。
    - 若模型由 Blender 导出后再进入 LaViC，**Blender 导出时必须取消 `Y-Up`（`export_yup=False`）**，避免在导出阶段提前写死坐标系转换。
    - 导入 LaViC 前，按 three.js 的约定以 **`Z` 轴为 Up** 处理，再执行一次 **绕 `X` 轴正向旋转 `90°`** 的转换。
    - 对飞机类模型，若已经确认 LaViC 侧采用这条链路，**禁止**再额外叠加旧的“Blender 侧预旋转”步骤，否则极易出现机身竖起、翻肚皮或机头方向错误。
    - **朝向归一化（强制检查）**:
      - 上述强制链路主要解决“模型放正”的问题，不自动保证机头一定朝 `+X`。
      - 若客户端中模型已经正立、机背朝上，但**机头仍朝 `+Y`**，则必须再做一次 **绕 `Z` 轴 `-90°`** 的朝向归一化，使机头对齐 `+X`。
      - `Y-9`、`C-130J` 已验证：运输机类 Rodin 模型在执行完导出链路后，常见剩余问题就是“姿态正确但机头朝 `+Y`”，此时补 `Z -90°` 即可。
      - 当前代码中，`Y-9` 与 `C-130J` 生成脚本已默认执行这一步，作为运输机资源包的额外保险。
    - **错误原因说明（必须理解）**:
      - 刚刚出错**不是研发流程错误**，也**不是模型生成失败**。
      - 根因是代码只固化了“坐标系转换 / 放正”这一步，却**漏掉了客户端最终朝向归一化检查**。
      - 也就是说，之前的错误更接近**流程遗漏**，不是 Rodin 本身错误；代码层面则表现为**缺少最后一步朝向修正逻辑**。
- **建议流程**:
    1. 飞机类优先执行上述“Blender `export_yup=False` + three.js `Z-Up` + `X +90°`”强制链路；
    2. 导入 LaViC 客户端查看；
    3. 若模型正立但机头朝 `+Y`，先执行 `Z -90°` 朝向归一化；
    4. 以“机头 `+X`、机背 `+Z`、机翼沿 `Y`”为最终目标做最小额外旋转；
    5. 确认后再重新打包覆盖 ZIP。

  - **舰船/航母类姿态规则（强制执行）**:
    - 舰船类模型最终验收姿态统一定义为：
      - **舰艏朝向 `+X`**
      - **甲板朝向 `+Z`**
      - **舰体横向沿 `Y`**
    - **姿态处理顺序必须固定**：
      1. 先检查舰体是否“立着”：
         - 若模型最长尺寸落在 `Z` 轴上，说明舰体被 Rodin 竖起来了；
         - 此时必须先做一次 **绕 `Y` 轴 `-90°`** 的“放平甲板”修正。
      2. 再检查舰体是否“侧翻”：
         - 若模型已经不是立着，但**`Z` 向高度仍大于 `Y` 向舰宽**，则说明舰船沿纵轴侧翻了；
         - 此时必须补一次 **绕 `X` 轴 `+90°`** 的“侧翻修正”。
      3. 再检查舰艏方向：
         - 若模型已经放平，但舰艏仍朝 `+Y`，则再做一次 **绕 `Z` 轴 `-90°`** 的朝向归一化。
      4. 最后重新落地：
         - 保证模型最低点回到 `Z=0`，避免转完后半沉或悬空。
    - 若模型在客户端中已经正立、甲板水平，但**舰艏仍朝 `+Y`**，则必须补一次 **绕 `Z` 轴 `-90°`** 的朝向归一化。
    - 这一步与飞机类的“放正”不同，舰船类常见问题不是翻转，而是**导出后保留了 Rodin 原始纵向朝向**，导致船头沿 `+Y/-Y` 而不是 `+X`。
    - 另外，舰船类还会出现另一种常见问题：**整艘船沿 `Z` 轴立起来**。这时不能只做 `Z` 轴旋转，必须先做 `Y -90°` 让甲板回到水平面。
    - 还有第三种常见问题：**舰体已经放倒，但整舰沿纵向侧翻**。这时也不能只做 `Z` 轴旋转，必须先做 `X +90°` 把甲板翻回水平。
    - **经验补充（易残留侧翻的航母/两栖攻击舰）**:
      - `辽宁舰`、`山东舰`、`R08 伊丽莎白女王号`、`R91 戴高乐号`、`LHA-6 美利坚号`、`DDH-183 出云号` 这类甲板舰，Rodin 生成后即使经过通用舰船姿态归一化，仍可能残留一次稳定的侧翻误差。
      - 当前工程中对此采用了更稳妥的兜底：在通用舰船归一化之后，额外补一次 **绕 `X` 轴 `+90°`** 的手动修正。
      - 这是当前针对这类甲板舰的工程化经验规则，优先保证客户端里甲板水平、舰体可用；若后续验证不再需要，可再收敛回通用规则。
      - 这条规则现在不再只写在文档里，已同步收敛到共享代码 `ship_orientation.py` 的已验证兜底表中；后续新舰型脚本应直接复用该共享逻辑，而不是各自临时手改。
      - 另外，生成完成后必须再做一次**客户端侧翻自检**：读取当前 `glb` 的长宽高，若出现 **`Y > Z`**，则判定这艘甲板舰在 LaViC 里仍会侧着显示，必须先补 `X +90°` 再打包。
      - 这条自检现在已经升级为**共享默认规则**：新生成的舰船/航母/两栖攻击舰/直升机驱逐舰，只要命中 `Y > Z`，就自动做 `X +90°`，不再依赖人工提醒。
    - **结论**：舰船类脚本在生成完成后，也必须执行一次客户端目标朝向检查；若要统一规则，默认将舰艏归一化到 `+X`，不要直接接受 Rodin 原始朝向。
    - **错误原因说明**:
      - 刚刚福建舰的问题不是 `iagnt_dynamics_ship_simple` 模板错误，也不是舰体翻转。
      - 根因是新建航母脚本时只覆盖了部分舰船姿态情况，先后漏掉了“舰体放平”和“侧翻修正”的完整判断，属于流程遗漏。
      - 因此后续所有舰船/航母脚本都应复用统一的 ship pose normalization 逻辑：**先放平，再去侧翻，再对艏向，最后落地**，而不是每个脚本各自临时调整。

  - **空对空导弹 / 比例导引导弹规则（强制执行）**:
    - `AIM-120` 这类空对空导弹必须优先复用案例：`examples/30csjkzBlueAirFighterMissileAgent.json`。
    - 生成时必须保留并对齐以下动力学配置：
      - `navigatableDynamics` = `iagnt_dynamics_pronav`
      - `missionableDynamics` = `iagnt_dynamics_linear_trajectory`
    - 动作指令不得替换成通用船舶/潜艇/地面单位动作，必须沿用案例里的导弹动作集，包括：
      - `LifeSpanInvalidStopStepClearRes`
      - `Recycle`
      - `UpdateRuntimeDistance`
      - `ExplodeWorking`
      - `InterceptWorking`
      - `SuppressWorking`
      - `InterfereWorking`
      - `ShiftNavigation`
      - `Launch`
    - 缩略图必须优先使用**完整导弹本体**、**干净背景**、**整弹侧视或 3/4 视图**，避免局部图、发射场景图、挂架图和纹理图。
    - 导弹 `glb` 在打包前必须做一次自检：最长轴应对齐 `+X`；若生成结果沿 `Y` 或 `Z` 拉长，必须先旋转归一化，再打包。
    - **导弹姿态压平（强制执行）**:
      - 不能只看轴对齐包围盒，否则会出现“AIM-9X 这种整体沿主轴翘起来”的情况。
      - 必须基于模型的**主惯性轴 / 主轴方向**做归一化：先把导弹纵轴对齐到 `+X`，再重新落地到 `Z=0`。
      - 当前工程里，`AIM-120`、`AIM-9X` 脚本已改为按主轴压平，而不是仅凭 `bbox` 判断。
  - **火炮 / 抛物弹道规则（强制执行）**:
    - `M777A2 155mm榴弹炮` 这类火炮平台若按炮弹/抛物线链路建模，`missionableDynamics` 必须切换为 `iagnt_dynamics_parabolic`。
    - 本地仓库若没有现成 `iagnt_dynamics_parabolic` 案例，不要继续沿用默认插件名，必须显式重写 `missionableDynamics` 与动作脚本里的插件调用。
    - 推荐以 `examples/08boundingMineAgent.json` 作为壳结构，再重写为抛物弹道链路，保留 6 个动作：`发射`、`打击`、`自毁`、`改变目标位置`、`能量消耗`、`设置能量消耗`。
    - 缩略图必须优先使用**单一、完整、清晰**的整门炮图，避免多人场景、发射场景、局部图和贴图。
    - 火炮 `glb` 在打包前必须做一次姿态自检：炮管主轴归一到 `+X`，若出现 `Z > Y` 的侧翻姿态，必须先补一次绕 `X` 轴压平，再重新落地到 `Z=0`。

    - **导弹质量闸门（强制执行）**:
      - 若 Rodin 结果出现“竖杆、支柱、插棍、明显离散零件”等非导弹主体结构，不允许直接打包。
      - 生成后必须检查：
        - `Z` 向高度是否异常接近 `X` 向长度；
        - 连通块数量是否异常碎裂；
        - 是否存在大的竖直 detached component。
      - 一旦命中上述问题，必须丢弃该 Rodin 结果，自动回退到**完整导弹主体 fallback mesh**，优先保证“像导弹、完整、可用”。

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
