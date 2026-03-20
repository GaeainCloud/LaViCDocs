import argparse
import glob
import json
import os
import sys

from jsonschema import Draft7Validator


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_files(schema_path, patterns):
    schema = load_json(schema_path)
    validator = Draft7Validator(schema)

    failures = []
    total = 0

    for pattern in patterns:
        for file_path in sorted(glob.glob(pattern)):
            total += 1
            try:
                data = load_json(file_path)
                errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
                if errors:
                    first = errors[0]
                    path = "/".join(map(str, first.path)) if first.path else "(root)"
                    failures.append((file_path, len(errors), path, first.message))
            except Exception as exc:
                failures.append((file_path, 1, "(read)", str(exc)))

    print(f"Validated files: {total}")
    print(f"Failures: {len(failures)}")

    if failures:
        print("\nValidation failures:")
        for file_path, count, path, msg in failures:
            print(f"- {file_path} | errors={count} | path={path} | {msg}")
        return 1

    print("All files passed schema validation.")
    return 0


def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    parser = argparse.ArgumentParser(
        description="Validate examples and generated model agent.json files."
    )
    parser.add_argument(
        "--schema",
        default=os.path.join(base_dir, "src", "校验代码参考", "AgentData_schema.json"),
        help="Schema path",
    )
    parser.add_argument(
        "--patterns",
        nargs="+",
        default=[
            os.path.join(base_dir, "examples", "*.json"),
            os.path.join(base_dir, "models", "*", "agent.json"),
        ],
        help="Glob patterns to validate",
    )
    args = parser.parse_args()
    return validate_files(args.schema, args.patterns)


if __name__ == "__main__":
    sys.exit(main())
