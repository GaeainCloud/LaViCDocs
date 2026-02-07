# LaViCDocs - Simulation Model Generation System

## Project Overview
LaViC simulation model lifecycle management system. Transforms natural language descriptions into standard simulation model asset packages (.zip) for import into the LaViC military simulation platform.

Core principle: **"One Prompt to Simulation Model"**

## Project Structure
```
AIAgentData/           # Core simulation models and generation pipeline
  ├── docs/            # Technical documentation (user manual, tech manual, GaeaScript)
  ├── examples/        # 30+ agent template JSON files (vehicle, aircraft, eVTOL, ship, missile, etc.)
  ├── models/          # 34 production-ready simulation model packages
  ├── src/             # 45+ Python scripts for model generation and processing
  │   ├── AI生成AgentData代码参考/  # LLM-based agent data generation reference code
  │   └── 校验代码参考/             # Schema validation (AgentData_schema.json)
  └── skill.md         # Full skill pipeline definition document
LaViCMCP/              # MCP server for LaViC API integration
RoadMap/               # Version roadmap
```

## Key Technical Details

### AgentData Schema
- Root: JSON array of agent objects
- Required fields: `agentKey`, `agentName`, `i18nLabels`, `agentNameI18n`, `agentKeyword`, `freelanceable`, `locatable`, `navigatable`, `missionable`, `operatable`, `agentType`, `agentCamp`, `model`, `waypoints`
- Schema file: `AIAgentData/src/校验代码参考/AgentData_schema.json`
- Validator: `AIAgentData/src/validator.py` (Draft-07)

### Dynamics Types
- `iagnt_dynamics_vehicle_simple` - Ground vehicles
- `iagnt_dynamics_carrier_based_aircraft` - Aircraft
- `HydroDynamics` - Underwater vehicles
- `MissileDynamics` - Missiles

### Asset Naming Convention
```
{ModelName}/
├── {ModelName}.png              # Thumbnail
├── {ModelName}_mil.png          # NATO APP-6D military symbol
└── {ModelName}_AI_Rodin.glb     # 3D model (Y-Up coordinate system)
```

### 3D Model Coordinate Correction (Mandatory)
1. Rotate -90 degrees around X axis (Z-Up to Y-Up)
2. Rotate 180 degrees around Y axis (facing correction)
Use `trimesh` library (see `src/fix_glb_rotation.py`)

### ZIP Packaging
- Encoding: UTF-8 (must support Chinese filenames)
- Structure: Flat (agent.json and asset folder at root level, no top-level wrapper folder)
- Tool: `src/zip_models.py`

## Commands
- Validate agent JSON: `python AIAgentData/src/validator.py --schema <schema_path> --data <data_path>`
- Fix agent JSON paths: `python AIAgentData/src/fix_and_zip_models.py`
- Generate military symbols: `python AIAgentData/src/gen_mil_symbols.py`
- Package models: `python AIAgentData/src/zip_models.py`

## Coding Conventions
- Python 3.x with UTF-8 encoding throughout
- Environment variable `PYTHONUTF8=1` required for Chinese filename support
- All paths use `os.path.join()` for cross-platform compatibility
- JSON files use `ensure_ascii=False` and `indent=2` for readability
