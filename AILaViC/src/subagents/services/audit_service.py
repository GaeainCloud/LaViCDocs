from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from agents.auditor.manager import AuditorAgent
from agents.auditor.probes.complexity import ComplexityProbe
from agents.auditor.probes.logic import LogicProbe
from agents.auditor.probes.physics import PhysicsProbe
from agents.auditor.probes.script import ScriptProbe
from agents.auditor.probes.tactics import TacticsProbe
from schemas.agent_data import ScenarioData
from schemas.audit_report import AuditReport, AuditSection


class AuditService:
    """Bridge legacy auditors/probes into subagents runtime."""

    def __init__(self) -> None:
        self._zip_auditor = AuditorAgent()
        self._probes = {
            "physics": PhysicsProbe(),
            "logic": LogicProbe(),
            "tactics": TacticsProbe(),
            "complexity": ComplexityProbe(),
            "script": ScriptProbe(),
        }

    def audit_zip(self, zip_path: str) -> Dict[str, Any]:
        report = self._zip_auditor.audit_zip(zip_path)
        return self._report_to_dict(report)

    def audit_scenario(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        schema = ScenarioData(**self._normalize_root(scenario_data))

        sections: Dict[str, Dict[str, Any]] = {}
        overall_status = "PASS"
        for name, probe in self._probes.items():
            section = probe.run(schema)
            section_dict = self._section_to_dict(section)
            sections[name] = section_dict
            if section_dict["status"] == "FAIL":
                overall_status = "FAIL"

        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": f"Audit completed. Overall status: {overall_status}",
            "sections": sections,
        }
        return report

    @staticmethod
    def collect_issues(report: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        sections = report.get("sections", {})
        for section_name, section in sections.items():
            for issue in section.get("issues", []):
                item = dict(issue)
                item.setdefault("section", section_name)
                issues.append(item)
        return issues

    @staticmethod
    def _normalize_root(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, list):
            if not raw:
                raise ValueError("JSON root list is empty")
            if not isinstance(raw[0], dict):
                raise ValueError("JSON root list first element must be an object")
            return raw[0]
        raise ValueError(f"Unexpected JSON root type: {type(raw)}")

    def _report_to_dict(self, report: AuditReport) -> Dict[str, Any]:
        result = {
            "timestamp": report.timestamp.isoformat(),
            "overall_status": report.overall_status,
            "summary": report.summary,
            "sections": {},
        }
        for name, section in report.sections.items():
            result["sections"][name] = self._section_to_dict(section)
        return result

    @staticmethod
    def _section_to_dict(section: AuditSection) -> Dict[str, Any]:
        return {
            "name": section.name,
            "status": section.status,
            "issues": [AuditService._issue_to_dict(issue) for issue in section.issues],
        }

    @staticmethod
    def _issue_to_dict(issue: Any) -> Dict[str, Any]:
        if hasattr(issue, "model_dump"):
            return issue.model_dump()
        if hasattr(issue, "dict"):
            return issue.dict()
        return dict(issue)

