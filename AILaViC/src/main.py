import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.append(str(PROJECT_ROOT / "src"))

from core.subagent_orchestrator import SubAgentOrchestrator
from subagents.state import init_state


def main() -> None:
    parser = argparse.ArgumentParser(description="AILaViC subagents orchestrator entrypoint")
    parser.add_argument("--intent", default="", help="Natural language scenario intent")
    parser.add_argument("--input", help="Scenario input path (.zip / .json / directory)")
    parser.add_argument("--output-dir", default="outputs", help="Artifact output directory")
    parser.add_argument("--state-output", help="Optional final state JSON file path")
    args = parser.parse_args()

    orchestrator = SubAgentOrchestrator()
    initial_state = init_state(
        user_intent=args.intent,
        input_path=args.input,
        output_dir=args.output_dir,
    )
    final_state = orchestrator.run(initial_state)

    payload = json.dumps(final_state, ensure_ascii=False, indent=2)
    print(payload)
    if args.state_output:
        out_path = Path(args.state_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
