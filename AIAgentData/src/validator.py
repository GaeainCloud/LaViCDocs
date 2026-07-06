import json
import argparse
import sys
from pathlib import Path

from config import SCHEMA_PATH, EXAMPLES_DIR
from logger import get_logger

log = get_logger(__name__)

try:
    from jsonschema import Draft7Validator
except ImportError:
    log.error("'jsonschema' module not found. Please run: pip install jsonschema")
    sys.exit(1)

def load_json(file_path):
    """Load JSON file safely."""
    file_path = Path(file_path)
    if not file_path.exists():
        log.error(f"File not found: {file_path}")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error(f"Failed to decode JSON from {file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        log.error(f"Unexpected error reading {file_path}: {e}")
        sys.exit(1)

def validate_agent_data(schema_path, data_path):
    """Validate AgentData JSON against the Schema using Draft-07."""
    log.info(f"Loading Schema from: {schema_path}")
    schema = load_json(schema_path)

    log.info(f"Loading Data from: {data_path}")
    data = load_json(data_path)

    log.info("Validating against JSON Schema Draft-07...")

    if not isinstance(data, list):
        log.warning("The data root is not a list. AgentData is typically an array of Agents.")

    try:
        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)

        if not errors:
            log.info("Data Validation Passed")
            return True
        else:
            log.error(f"Data Validation Failed with {len(errors)} errors:")
            for i, error in enumerate(errors, 1):
                path_str = '/'.join(map(str, error.path)) if error.path else "(root)"
                schema_path_str = '/'.join(map(str, error.schema_path))
                log.error(f"[Error {i}] Path: {path_str}")
                log.error(f"  Message: {error.message}")
                log.error(f"  Schema Rule: {schema_path_str}")
            return False

    except Exception as e:
        log.error(f"Unexpected error during validation: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate AgentData JSON against Schema (Draft-07).")
    parser.add_argument("--schema", default=str(SCHEMA_PATH), help="Path to the AgentData schema file")
    parser.add_argument("--data", default=str(EXAMPLES_DIR / "03evtolAgent.json"), help="Path to the AgentData JSON file to validate")
    args = parser.parse_args()
    validate_agent_data(args.schema, args.data)
