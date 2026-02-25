import sys
import os
import json
from pathlib import Path

# Setup paths
# Add the 'src' directory to sys.path for package imports (agents, utils, etc.)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
# Add the project root directory to sys.path for config imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from agents.auditor.manager import AuditorAgent
from schemas.audit_report import AuditReport

def main():
    # Target the fixed zip file
    # Assuming the script is run from the project root or we need absolute path
    # Let's use absolute path as in original script
    zip_path = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples\想定_防空反导-v1.60.9-修复版.zip"
    
    if not os.path.exists(zip_path):
        print(f"Error: File not found at {zip_path}")
        return

    agent = AuditorAgent()
    print(f"Running Physics Auditor on {zip_path}...")
    
    try:
        report = agent.audit_zip(zip_path)
        
        # Focus on Physics Consistency
        physics_section = report.sections.get("physics")
        
        if not physics_section:
            print("Error: No physics audit section found in report.")
            return
            
        print("\n" + "="*50)
        print("PHYSICS AUDIT REPORT")
        print("="*50)
        print(f"Status: {physics_section.status}")
        
        issues = physics_section.issues
        
        # Extract Summary Issues
        summary_issues = [i for i in issues if i.code in ["PHY_SUMMARY_PASS", "PHY_SUMMARY_FAIL"]]
        detail_issues = [i for i in issues if i.code not in ["PHY_SUMMARY_PASS", "PHY_SUMMARY_FAIL"]]
        
        # --- GENERATE MARKDOWN REPORT ---
        md_lines = []
        md_lines.append("# Physics Compliance Audit Report")
        md_lines.append(f"**Date**: {report.timestamp}")
        md_lines.append(f"**Target**: {os.path.basename(zip_path)}")
        md_lines.append(f"**Overall Status**: {physics_section.status}")
        md_lines.append("")
        md_lines.append("## Entity Inspection Details")
        
        if summary_issues:
            # Sort by entity name for consistent output
            summary_issues.sort(key=lambda x: x.entity_id or "")
            
            import json
            
            for idx, item in enumerate(summary_issues, 1):
                # item.message format: "JSON_DATA:{...}"
                try:
                    if item.message.startswith("JSON_DATA:"):
                        json_str = item.message[len("JSON_DATA:"):]
                        stats = json.loads(json_str)
                        
                        limits = stats.get("limits", {})
                        
                        # Helper to format check result
                        def check_line(label, obs_key, limit_key, unit="", multiplier=1.0, is_min=False):
                            obs = stats.get(obs_key, 0.0) * multiplier
                            limit = limits.get(limit_key, 0.0) * multiplier
                            
                            # Pass/Fail logic
                            status = "PASS"
                            if is_min:
                                if obs < limit: status = "FAIL"
                            else:
                                if obs > limit: status = "FAIL"
                            
                            # For Range/Endurance, limits might be huge (infinite)
                            limit_str = f"{limit:.1f}"
                            if limit > 1e6 and limit_key == "max_endurance": limit_str = "Inf"
                            
                            return f"  - {label}: {obs:.1f} {unit} (Limit: {limit_str} {unit}) - **{status}**"

                        def check_count(label, obs_key, limit=0):
                            obs = stats.get(obs_key, 0)
                            status = "PASS" if obs <= limit else "FAIL"
                            return f"  - {label}: {obs} violations - **{status}**"
                        
                        def check_ammo(label, obs_key, limit_key):
                            obs = stats.get(obs_key, 0)
                            limit = limits.get(limit_key, 0)
                            status = "PASS" if obs <= limit else "FAIL"
                            return f"  - {label}: Used {obs} / Cap {limit} - **{status}**"

                        md_lines.append(f"### {idx}. {item.entity_id}")
                        md_lines.append(f"**Status**: {'PASS' if item.code == 'PHY_SUMMARY_PASS' else 'FAIL'}")
                        
                        # 1.1.1 L1
                        md_lines.append(f"#### 1.1.1 L1: 运动学一致性 (Kinematics)")
                        md_lines.append(check_line("极速限制 (Maximum Speed Cap)", "max_speed", "max_speed", "m/s"))
                        md_lines.append(check_count("失速与最小速度阈值 (Stall Speed Threshold)", "stall_warnings"))
                        md_lines.append(check_count("时空连续性检测 (Temporal Continuity)", "teleport_count"))
                        md_lines.append(check_line("机动过载限制 (G-Force)", "max_g", "max_g", "G"))
                        
                        # 1.1.2 L2
                        md_lines.append(f"#### 1.1.2 L2: 环境与空间限制 (Environment & Space)")
                        md_lines.append(check_count("介质排他性 (Domain Validity)", "domain_violations"))
                        md_lines.append(check_line("最大潜深 (Min Altitude)", "min_alt", "min_alt", "m", is_min=True))
                        md_lines.append(check_line("实用升限 (Max Altitude)", "max_alt", "max_alt", "m"))
                        md_lines.append(check_count("地形避障与防撞 (Terrain Collision)", "terrain_violations"))
                        md_lines.append(check_count("地球曲率视线遮挡 (Radar Horizon)", "los_violations"))
                        
                        # 1.1.3 L3
                        md_lines.append(f"#### 1.1.3 L3: 资源与能量守恒 (Resources)")
                        md_lines.append(check_ammo("弹药硬约束 (Hard Ammo Limit)", "ammo_used", "ammo_capacity"))
                        md_lines.append(check_line("最大物理航程 (Max Ferry Range)", "max_range", "max_range", "km", multiplier=0.001))
                        md_lines.append(check_line("最大留空/作战时间 (Max Endurance)", "max_endurance", "max_endurance", "h", multiplier=1.0/3600.0))
                        md_lines.append(f"  - 挂载互斥与载重限制 (Payload Mutex & Weight): N/A (No Payload Data) - **PASS**")
                        
                        md_lines.append("")
                        
                    else:
                        # Fallback for old format if any
                        md_lines.append(f"{idx}. {item.message}")
                except Exception as e:
                    md_lines.append(f"{idx}. Error parsing data for {item.entity_id}: {e}")

        # Save Markdown Report
        # Save to src/agents/auditor/physics_check_report.md (same dir as this script)
        report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "physics_check_report.md")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
            
        print(f"\n📄 Markdown Report Generated: {report_path}")
        print("-" * 50)
        
        # Also print simplified summary to console
        if summary_issues:
            print("\n" + "="*50)
            print("ENTITY COMPLIANCE SUMMARY (See Report for Details)")
            print("="*50)
            for idx, item in enumerate(summary_issues, 1):
                status = "PASS" if item.code == 'PHY_SUMMARY_PASS' else "FAIL"
                print(f"{idx}. {item.entity_id} - {status}")

        if not detail_issues:
            if not summary_issues:
                print("\n✅ No physics violations found. The scenario complies with physical laws.")
        else:
            print(f"\nFound {len(detail_issues)} detailed physics issues:")
            
            # Group by severity
            criticals = [i for i in detail_issues if i.severity in ["CRITICAL", "ERROR", "FAIL"]]
            warnings = [i for i in detail_issues if i.severity in ["WARNING", "WARN"]]
            infos = [i for i in detail_issues if i.severity not in ["CRITICAL", "ERROR", "FAIL", "WARNING", "WARN"]]
            
            if criticals:
                print(f"\n🔴 CRITICAL VIOLATIONS ({len(criticals)}):")
                for item in criticals:
                    print(f"  - [{item.code}] {item.message}")
                    print(f"    Entity: {item.entity_id} | Time: {item.time_step} | Evidence: {item.evidence}")
            
            if warnings:
                print(f"\n🟡 WARNINGS ({len(warnings)}):")
                for item in warnings:
                    print(f"  - [{item.code}] {item.message}")
                    print(f"    Entity: {item.entity_id} | Time: {item.time_step} | Evidence: {item.evidence}")
                    
            if infos:
                print(f"\n🔵 INFO ({len(infos)}):")
                for item in infos:
                    print(f"  - [{item.code}] {item.message}")

        # Also check Integrity (Resources) as per skill.md
        integrity_section = report.sections.get("integrity")
        if integrity_section:
             print("\n" + "-"*30)
             print(f"Resource Integrity: {integrity_section.status}")
             if integrity_section.issues:
                 for issue in integrity_section.issues:
                     print(f"  - {issue.message}")

    except Exception as e:
        print(f"Fatal Error during audit: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
