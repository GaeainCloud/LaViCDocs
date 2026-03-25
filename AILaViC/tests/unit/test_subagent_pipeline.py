import os
import shutil
import sys
import unittest
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from core.subagent_orchestrator import SubAgentOrchestrator
from subagents.state import init_state


class TestSubAgentPipeline(unittest.TestCase):
    def setUp(self):
        self.orchestrator = SubAgentOrchestrator()
        self.output_dir = Path(__file__).resolve().parents[2] / "outputs" / "unit_tests"
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

    def tearDown(self):
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

    def test_generate_mode_pipeline(self):
        state = init_state(
            user_intent="构建一个防空反导演练想定",
            output_dir=str(self.output_dir),
        )
        final_state = self.orchestrator.run(state)

        self.assertEqual(final_state.get("status"), "SUCCEEDED")
        self.assertIn("scenario_data", final_state)
        self.assertIn("execution_plan", final_state)
        self.assertTrue(Path(final_state["execution_plan"]["scenario_path"]).exists())
        self.assertTrue(Path(final_state["execution_plan"]["audit_report_path"]).exists())

    def test_existing_json_pipeline(self):
        sample_json = (
            Path(__file__).resolve().parents[2]
            / "knowledge_base"
            / "examples"
            / "想定_防空反导-v1.60.9-修复版"
            / "simulation.json"
        )
        state = init_state(
            user_intent="审计防空反导样例",
            input_path=str(sample_json),
            output_dir=str(self.output_dir),
        )
        final_state = self.orchestrator.run(state)

        self.assertEqual(final_state.get("status"), "SUCCEEDED")
        self.assertEqual(final_state.get("source_type"), "json")
        report = final_state.get("audit_report", {})
        sections = report.get("sections", {})
        self.assertIn("physics", sections)
        self.assertIn("logic", sections)


if __name__ == "__main__":
    unittest.main()

