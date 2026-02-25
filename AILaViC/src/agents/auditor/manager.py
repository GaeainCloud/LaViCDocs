from typing import Dict, Any, List
from pathlib import Path
import logging
import json

from schemas.audit_report import AuditReport, AuditIssue
from schemas.agent_data import ScenarioData
from utils.file_handler import FileHandler
from agents.auditor.probes.integrity import IntegrityProbe
from agents.auditor.probes.physics import PhysicsProbe
from agents.auditor.probes.logic import LogicProbe
from agents.auditor.probes.tactics import TacticsProbe
from agents.auditor.probes.complexity import ComplexityProbe
from agents.auditor.probes.script import ScriptProbe

logger = logging.getLogger(__name__)

class AuditorAgent:
    def __init__(self):
        self.probes = {
            "integrity": IntegrityProbe(),
            "physics": PhysicsProbe(),
            "logic": LogicProbe(),
            "tactics": TacticsProbe(),
            "complexity": ComplexityProbe(),
            "script": ScriptProbe()
        }

    def audit_zip(self, zip_path: str) -> AuditReport:
        """
        审计 Zip 格式的想定包
        """
        report = AuditReport(overall_status="PASS", summary="Audit started")
        temp_dir = None
        
        try:
            # 1. 解压
            logger.info(f"Extracting zip: {zip_path}")
            temp_dir = FileHandler.extract_zip(zip_path)
            
            # 2. 运行资源完整性检查 (需要目录上下文)
            integrity_section = self.probes["integrity"].run({"temp_dir": temp_dir})
            report.sections["integrity"] = integrity_section
            
            if integrity_section.status == "FAIL":
                report.overall_status = "FAIL"
                report.summary = "Integrity check failed. Stopping further analysis."
                # 尝试继续，除非关键文件丢失
            
            # 3. 解析 JSON 数据
            try:
                # 优先查找 simulation.json
                json_path = str(Path(temp_dir) / "simulation.json")
                if not Path(json_path).exists():
                     # Fallback to general search
                     json_path = FileHandler.find_main_json(temp_dir)
                
                raw_data = FileHandler.load_json(json_path)
                
                scenario_data = self._parse_to_schema(raw_data)
                
            except Exception as e:
                report.overall_status = "FAIL"
                report.add_section("JSON Parsing", "FAIL", [AuditIssue(severity="ERROR", code="JSON_ERR", message=str(e))])
                return report

            # 4. 运行基于数据的探针
            data_probes = ["physics", "logic", "tactics", "complexity", "script"]
            for name in data_probes:
                probe = self.probes[name]
                section = probe.run(scenario_data)
                report.sections[name] = section
                if section.status == "FAIL":
                    report.overall_status = "FAIL"

            report.summary = f"Audit completed. Overall status: {report.overall_status}"

        except Exception as e:
            logger.error(f"Audit failed: {e}", exc_info=True)
            report.overall_status = "FAIL"
            report.summary = f"Audit failed with exception: {str(e)}"
        
        finally:
            # 5. 清理
            if temp_dir:
                FileHandler.cleanup(temp_dir)
                
        return report

    def _parse_to_schema(self, raw_data: Any) -> ScenarioData:
        # Handle list root
        data_dict = {}
        if isinstance(raw_data, list):
            if len(raw_data) > 0:
                data_dict = raw_data[0]
            else:
                raise ValueError("JSON root is an empty list")
        elif isinstance(raw_data, dict):
            data_dict = raw_data
        else:
            raise ValueError(f"Unexpected JSON root type: {type(raw_data)}")
            
        return ScenarioData(**data_dict)
