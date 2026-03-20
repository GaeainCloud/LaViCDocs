import argparse
import os
import time

from cli import SCRIPT_MAP, run_script


PIPELINES = {
    "full": [
        "gen-fighters",
        "gen-carriers",
        "fetch-images",
        "gen-vehicles",
        "gen-mil-symbols",
        "fix-zip",
        "validate-all",
    ],
    "air": ["gen-fighters", "gen-carriers", "fix-zip", "validate-all"],
    "ground": ["fetch-images", "gen-vehicles", "gen-mil-symbols", "fix-zip", "validate-all"],
    "sm3": ["gen-sm3", "validate-all"],
    "validate": ["validate-all"],
}


RODIN_REQUIRED_STEPS = {"gen-fighters", "gen-carriers", "gen-sm3"}


def parse_list(text):
    return [item.strip() for item in text.split(",") if item.strip()]


def resolve_steps(args):
    if args.steps:
        steps = parse_list(args.steps)
    else:
        steps = list(PIPELINES[args.pipeline])

    if args.skip:
        skipped = set(parse_list(args.skip))
        steps = [s for s in steps if s not in skipped]
    return steps


def validate_steps(steps):
    unknown = [step for step in steps if step not in SCRIPT_MAP]
    if unknown:
        raise ValueError(f"Unknown steps: {', '.join(unknown)}")
    if "pipeline" in steps:
        raise ValueError("Step 'pipeline' cannot be nested inside pipeline execution.")


def require_env_for_steps(steps):
    if any(step in RODIN_REQUIRED_STEPS for step in steps):
        if not os.getenv("RODIN_API_KEY", "").strip():
            raise RuntimeError(
                "RODIN_API_KEY is required for selected steps. "
                "Set it in environment before running the pipeline."
            )


def build_parser():
    parser = argparse.ArgumentParser(description="Pipeline orchestrator for AIAgentData.")
    parser.add_argument(
        "--pipeline",
        choices=sorted(PIPELINES.keys()),
        default="full",
        help="Predefined pipeline preset.",
    )
    parser.add_argument(
        "--steps",
        default="",
        help="Override with a comma-separated custom step list, e.g. gen-fighters,fix-zip,validate-all",
    )
    parser.add_argument(
        "--skip",
        default="",
        help="Comma-separated steps to skip from selected pipeline.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned execution without running scripts.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue remaining steps even if one step fails.",
    )
    parser.add_argument(
        "--allow-placeholder",
        action="store_true",
        help="Set AIALAVIC_ALLOW_PLACEHOLDER=1 for this run.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    steps = resolve_steps(args)
    if not steps:
        print("No steps to run after filtering.")
        return 0

    validate_steps(steps)
    if not args.dry_run:
        require_env_for_steps(steps)

    if args.allow_placeholder:
        os.environ["AIALAVIC_ALLOW_PLACEHOLDER"] = "1"

    print("Pipeline steps:")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step} -> {SCRIPT_MAP[step]}")

    if args.dry_run:
        print("Dry-run enabled; no scripts executed.")
        return 0

    started = time.time()
    results = []

    for step in steps:
        step_start = time.time()
        code = run_script(step, [])
        duration = round(time.time() - step_start, 2)
        results.append((step, code, duration))

        if code != 0 and not args.continue_on_error:
            print(f"Step failed: {step} (exit={code})")
            break

    total = round(time.time() - started, 2)
    print("\nExecution summary:")
    for step, code, duration in results:
        status = "OK" if code == 0 else "FAIL"
        print(f"  - {step:15s} {status:4s} {duration:>7.2f}s")
    print(f"Total time: {total:.2f}s")

    if any(code != 0 for _, code, _ in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
