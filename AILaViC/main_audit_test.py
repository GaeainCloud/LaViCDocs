import sys
import os
import json
import zipfile
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agents.auditor.manager import AuditorAgent
from config.settings import settings

def create_mock_zip(filename):
    """创建用于测试的 Mock Zip 文件 (匹配真实 Schema)"""
    print(f"Creating mock zip: {filename}")
    
    # 模拟数据：List Root, agentInstances, waypoints
    data = [
        {
            "simulation": {
                "simulationName": "Mock Scenario",
                "simulationStatus": "Draft"
            },
            "agentInstances": [
                {
                    "agentKey": "key-1",
                    "agentInstId": "entity-1",
                    "instanceName": "FastJet",
                    "agentType": "Aircraft",
                    "waypoints": [
                        {
                            "wpsKeyword": "route1",
                            "wps": [
                                {
                                    "wpsCore": [120.0, 24.0, 1000.0],
                                    "speed": 40.0 # Exceeds 35
                                }
                            ]
                        }
                    ]
                },
                {
                    "agentKey": "key-2",
                    "instanceName": "SlowBoat",
                    "agentType": "Ship",
                    "waypoints": [
                         {
                            "wpsKeyword": "route1",
                            "wps": [
                                {
                                    "wpsCore": [120.0, 24.0, 0.0],
                                    "speed": 10.0
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
    
    # 创建资源文件
    with zipfile.ZipFile(filename, 'w') as zf:
        zf.writestr("simulation.json", json.dumps(data, indent=2))
        # map.dat no longer required, but let's add a dummy file just in case
        
    return filename

def main():
    zip_name = "test_scenario_v2.zip"
    create_mock_zip(zip_name)
    
    try:
        agent = AuditorAgent()
        print(f"Starting audit on {zip_name}...")
        report = agent.audit_zip(zip_name)
        
        print("\n" + "="*30)
        print("AUDIT REPORT SUMMARY")
        print("="*30)
        print(f"Overall Status: {report.overall_status}")
        print(f"Summary: {report.summary}")
        print("-" * 20)
        
        for name, section in report.sections.items():
            print(f"[{name.upper()}] Status: {section.status}")
            for issue in section.issues:
                print(f"  - [{issue.severity}] {issue.code}: {issue.message}")
                
        # 验证结果
        assert report.sections["integrity"].status == "PASS"
        assert report.sections["physics"].status == "FAIL" # Expect failure due to 40.0 knots
        
        print("\nTest Passed: Auditor correctly identified issues in new schema.")
        
    finally:
        # Cleanup mock zip
        if os.path.exists(zip_name):
            os.remove(zip_name)

if __name__ == "__main__":
    main()
