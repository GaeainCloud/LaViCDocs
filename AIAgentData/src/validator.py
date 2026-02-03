import json
import argparse
import sys
import os

# Try to import jsonschema
try:
    from jsonschema import validate, ValidationError, Draft7Validator
except ImportError:
    print("Error: 'jsonschema' module not found. Please run: pip install jsonschema")
    sys.exit(1)

def load_json(file_path):
    """Load JSON file safely."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from {file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: An unexpected error occurred while reading {file_path}: {e}")
        sys.exit(1)

def validate_agent_data(schema_path, data_path):
    """
    Validate AgentData JSON against the Schema using Draft-07.
    """
    print(f"Loading Schema from: {schema_path}")
    schema = load_json(schema_path)
    
    print(f"Loading Data from: {data_path}")
    data = load_json(data_path)
    
    print("Validating against JSON Schema Draft-07...")
    
    if not isinstance(data, list):
         print("Warning: The data root is not a list. AgentData is typically an array of Agents.")

    try:
        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        
        if not errors:
            print("\n✅ Data Validation Passed")
            return True
        else:
            print(f"\n❌ Data Validation Failed with {len(errors)} errors:")
            for i, error in enumerate(errors, 1):
                path_str = '/'.join(map(str, error.path)) if error.path else "(root)"
                schema_path_str = '/'.join(map(str, error.schema_path))
                
                print(f"\n[Error {i}]")
                print(f"  Path: {path_str}")
                print(f"  Message: {error.message}")
                print(f"  Schema Rule: {schema_path_str}")
            return False
            
    except Exception as e:
        print(f"An unexpected error occurred during validation: {e}")
        return False

if __name__ == "__main__":
    # Absolute paths based on the project structure
    # Using raw strings for Windows paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_schema = os.path.join(base_dir, "src", "校验代码参考", "AgentData_schema.json")
    default_data = os.path.join(base_dir, "examples", "03evtolAgent.json")

    parser = argparse.ArgumentParser(description="Validate AgentData JSON against Schema (Draft-07).")
    parser.add_argument("--schema", default=default_schema, help="Path to the AgentData schema file")
    parser.add_argument("--data", default=default_data, help="Path to the AgentData JSON file to validate")
    
    args = parser.parse_args()
    
    validate_agent_data(args.schema, args.data)
