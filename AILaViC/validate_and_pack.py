import json
import os
import zipfile
import jsonschema
from jsonschema import validate

# Paths
base_dir = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC"
fixed_dir_name = "想定_防空反导-v1.60.9-修复版"
fixed_dir_path = os.path.join(base_dir, "knowledge_base", "examples", fixed_dir_name)
json_path = os.path.join(fixed_dir_path, "simulation.json")
schema_dir = os.path.join(base_dir, "src", "schemas")
output_zip_path = os.path.join(base_dir, "knowledge_base", "examples", f"{fixed_dir_name}.zip")

# Load JSON
print(f"Loading {json_path}...")
with open(json_path, 'r', encoding='utf-8') as f:
    sim_data = json.load(f)

sim_item = sim_data[0]

# Load Schemas
schemas = {}
schema_files = [
    "AgentData_schema.json",
    "doctrine_schema.json",
    "doe.schema.json",
    "patterndata_schema.json"
]

print("Loading schemas...")
for s_file in schema_files:
    s_path = os.path.join(schema_dir, s_file)
    with open(s_path, 'r', encoding='utf-8') as f:
        schemas[s_file] = json.load(f)

# Validation Function
def validate_section(data, schema_name, section_name="Root"):
    print(f"Validating {section_name} against {schema_name}...")
    try:
        validate(instance=data, schema=schemas[schema_name])
        print(f"  [PASS] {section_name} validation passed.")
        return True
    except jsonschema.ValidationError as e:
        print(f"  [FAIL] {section_name} validation failed: {e.message}")
        print(f"  Path: {list(e.path)}")
        return False
    except Exception as e:
        print(f"  [ERROR] {section_name} validation error: {str(e)}")
        return False

# 1. Validate Agent Instances
valid = True
if 'agentInstances' in sim_item:
    if not validate_section(sim_item['agentInstances'], "AgentData_schema.json", "agentInstances"):
        valid = False
else:
    print("  [WARN] 'agentInstances' not found in simulation item.")

if 'agents' in sim_item:
    if not validate_section(sim_item['agents'], "AgentData_schema.json", "agents"):
        valid = False

# 2. Validate Patterns
if 'agentRunningPatterns' in sim_item:
    if not validate_section(sim_item['agentRunningPatterns'], "patterndata_schema.json", "agentRunningPatterns"):
        valid = False

# 3. Validate Doctrine (Root Item)
if not validate_section(sim_item, "doctrine_schema.json", "Simulation Item (Doctrine)"):
    valid = False

# 4. Validate DoE (Root Item)
# doe.schema defines properties like "doeConfigSig".
# Only validate if doeConfigSig is present, as this is a simulation file, not necessarily a DoE config.
if 'doeConfigSig' in sim_item:
    if not validate_section(sim_item, "doe.schema.json", "Simulation Item (DoE)"):
        valid = False
else:
    print("  [INFO] Skipping DoE validation: 'doeConfigSig' not found (Not a DoE configuration).")

if not valid:
    print("\n[STOP] Schema validation failed. Aborting packaging.")
    exit(1)

print("\n[PASS] All schema validations passed.")

# Resource Validation
print("\nChecking resources...")
missing_files = []

def check_resources_v2(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            check_resources_v2(v)
    elif isinstance(obj, list):
        for item in obj:
            check_resources_v2(item)
    elif isinstance(obj, str):
        prefix = "想定_防空反导/"
        # Check strict prefix match as observed in the file
        if obj.startswith(prefix):
             rel_path = obj
             full_path = os.path.join(fixed_dir_path, rel_path)
             if not os.path.exists(full_path):
                 missing_files.append(rel_path)
                 print(f"  [MISSING] {rel_path}")

check_resources_v2(sim_item)

if missing_files:
    print(f"\n[STOP] Found {len(missing_files)} missing resource files. Aborting packaging.")
    exit(1)

print("\n[PASS] Resource check passed.")

# Packaging
print(f"\nCreating ZIP archive at {output_zip_path}...")
try:
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk relative to fixed_dir_path
        for root, dirs, files in os.walk(fixed_dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, fixed_dir_path)
                # Ensure utf-8 encoding is used (default in Python 3 zipfile)
                print(f"  Adding {arcname}")
                zipf.write(file_path, arcname)
    print("ZIP creation complete.")
except Exception as e:
    print(f"[ERROR] Failed to create ZIP: {e}")
    exit(1)
