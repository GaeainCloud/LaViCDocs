import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agents.auditor.manager import AuditorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    # Real zip path
    zip_path = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\src\schemas\想定_防空反导-v1.60.9-null-2026年02月10日07时01分46秒.zip"
    
    if not os.path.exists(zip_path):
        print(f"Error: Zip file not found at {zip_path}")
        return

    try:
        agent = AuditorAgent()
        print(f"Starting audit on {os.path.basename(zip_path)}...")
        report = agent.audit_zip(zip_path)
        
        print("\n" + "="*30)
        print("AUDIT REPORT SUMMARY")
        print("="*30)
        print(f"Overall Status: {report.overall_status}")
        print(f"Summary: {report.summary}")
        print("-" * 20)
        
        for name, section in report.sections.items():
            print(f"[{name.upper()}] Status: {section.status}")
            if section.issues:
                for issue in section.issues:
                    print(f"  - [{issue.severity}] {issue.code}: {issue.message}")
            else:
                print("  (No issues)")
                
    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    main()
