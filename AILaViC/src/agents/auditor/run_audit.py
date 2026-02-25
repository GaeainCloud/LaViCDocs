
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from agents.auditor.manager import AuditorAgent
from schemas.audit_report import AuditReport

def main():
    zip_path = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples\想定_防空反导-v1.60.9-修复版.zip"
    
    if not os.path.exists(zip_path):
        print(f"Error: File not found at {zip_path}")
        return

    agent = AuditorAgent()
    print(f"Auditing {zip_path}...")
    
    report = agent.audit_zip(zip_path)
    
    # Generate Markdown Report
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../audit_report.md'))
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# 仿真审计报告 (Simulation Audit Report)\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**文件源**: `{os.path.basename(zip_path)}`\n")
        
        status_icon = "🟢" if report.overall_status == "PASS" else "🔴"
        f.write(f"**总体状态**: {status_icon} {report.overall_status}\n\n")
        
        f.write("## 1. 摘要 (Summary)\n")
        f.write(f"{report.summary}\n\n")
        
        f.write("## 2. 详细审计结果 (Detailed Results)\n\n")
        
        for section_name, section in report.sections.items():
            f.write(f"### {section_name.upper()}\n")
            sec_icon = "🟢" if section.status == "PASS" else "🔴"
            f.write(f"**状态**: {sec_icon} {section.status}\n\n")
            
            if not section.issues:
                f.write("> 无违规项 (No issues found)\n\n")
                continue
                
            f.write("| 级别 | 代码 | 实体 (Instance/Agent) | 描述 | 证据 |\n")
            f.write("|---|---|---|---|---|\n")
            
            for issue in section.issues:
                sev_icon = "🔴" if issue.severity in ["CRITICAL", "ERROR", "FAIL"] else "🟡" if issue.severity in ["WARNING", "WARN"] else "🔵"
                
                entity_display = issue.entity_id or "N/A"
                if issue.agent_name and issue.agent_name != "N/A":
                    entity_display += f" <br> ({issue.agent_name})"
                
                f.write(f"| {sev_icon} {issue.severity} | `{issue.code}` | {entity_display} | {issue.message} | `{issue.evidence}` |\n")
            
            f.write("\n")
            
    print(f"Markdown report generated at: {output_path}")

if __name__ == "__main__":
    main()
