
import sys
import os
import json
from pathlib import Path

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from utils.file_handler import FileHandler

def main():
    zip_path = r"d:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples\想定_防空反导-v1.60.9-null-2026年02月10日07时01分46秒.zip"
    temp_dir = FileHandler.extract_zip(zip_path)
    
    try:
        json_path = FileHandler.find_main_json(temp_dir)
        print(f"Found JSON: {json_path}")
        
        data = FileHandler.load_json(json_path)
        # Handle list root
        if isinstance(data, list):
            data = data[0]
            
        # Check agents
        agents = data.get("agentInstances", [])
        print(f"Found {len(agents)} agents.")
        
        for agent in agents:
            name = agent.get("instanceName")
            if name in ["Conflict Dolphin", "Majestic Penguin"]: # Check problem agents
                print(f"\n--- Agent: {name} ---")
                wps = []
                for group in agent.get("waypoints", []):
                    for wp in group.get("wps", []):
                        core = wp.get("wpsCore") # [lon, lat, alt, time, ...]
                        if core:
                            wps.append(core)
                
                print(f"Total Waypoints: {len(wps)}")
                # Print first few
                for i, wp in enumerate(wps[:5]):
                    print(f"  WP[{i}]: {wp}")
                
                # Check for duplicate times
                times = [wp[3] for wp in wps if len(wp) > 3]
                duplicates = set([x for x in times if times.count(x) > 1])
                if duplicates:
                    print(f"  Duplicate times found: {duplicates}")

    finally:
        FileHandler.cleanup(temp_dir)

if __name__ == "__main__":
    main()
