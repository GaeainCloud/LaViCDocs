import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_BASE_URL = os.getenv("LAVIC_API_BASE_URL")
DEFAULT_USER_ID = os.getenv("LAVIC_USER_ID")
API_TOKEN = os.getenv("LAVIC_API_TOKEN")

print(f"Testing with User ID: {DEFAULT_USER_ID}")
print(f"Testing with Token: {API_TOKEN[:10]}...")

def make_request(method, endpoint, params=None, json_data=None):
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "X-UserId": DEFAULT_USER_ID,
        "Content-Type": "application/json",
        "Authorization": f"admin-Token={API_TOKEN}"
    }
    print(f"\nRequesting {method} {url}...")
    try:
        resp = requests.request(method, url, params=params, json=json_data, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCCESS!")
            try:
                data = resp.json()
                if "data" in data and "content" in data["data"]:
                    content = data["data"]["content"]
                    total = data["data"].get("totalElements", "Unknown")
                    print(f"Total Elements: {total}")
                    # print(f"{'ID':<30} | {'Name':<30} | {'Created By':<20} | {'Created By ID'}")
                    # print("-" * 100)
                    for item in content:
                        # Try different name fields depending on endpoint
                        name = item.get('simulationName') or item.get('agentName') or item.get('patternName') or "Unknown"
                        sig = item.get('simulationSig') or item.get('agentKey') or item.get('patternSig') or "Unknown"
                        
                        audit = item.get('audit', {})
                        created_by = audit.get('createdBy', 'Unknown')
                        # created_by_id = audit.get('createdById', 'Unknown')
                        print(f"{sig:<30} | {name:<30} | {created_by:<20}")
                else:
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
            except:
                print(resp.text[:500])
        else:
            print(f"Error: {resp.text[:500]}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    print("\n=== Verifying MCP Tool Logic ===")

    print("\n--- 1. Search '微想定' in Scenarios (getAllSysOfSysStep) with simulationTag=1 ---")
    # Adding simulationTag=1 to params
    data = make_request("GET", "/getAllSysOfSysStep", params={"pageNum": 1, "pageSize": 100, "simulationTag": "1"})
    if data and "data" in data:
        content = data["data"].get("content", [])
        print(f"Total Scenarios Found: {data['data'].get('totalElements')}")
        print(f"{'ID':<30} | {'Name':<30} | {'Created By'}")
        print("-" * 80)
        for item in content:
            audit = item.get('audit', {})
            created_by = audit.get('createdBy', 'Unknown')
            print(f"{item.get('simulationSig'):<30} | {item.get('simulationName'):<30} | {created_by}")
    else:
        print("Error or no data:", json.dumps(data, ensure_ascii=False)[:200])
    
    # Exit early to see output
    exit()

    print("\n--- 2. Search '微想定' in Agent Patterns (getAllAgentPattern) ---")
    data = make_request("GET", "/getAllAgentPattern", params={"pageNum": 1, "pageSize": 10})
    if data and "data" in data and isinstance(data["data"], list):
        patterns = data["data"]
        print(f"Total Patterns Found: {len(patterns)}")
        if len(patterns) > 0:
            print("First pattern sample:", json.dumps(patterns[0], ensure_ascii=False, indent=2))
        
        print(f"{'Sig':<30} | {'Name':<30}")
        print("-" * 60)
        for p in patterns:
            name = p.get('patternName')
            if name is None:
                # Try to find name in nested objects if any
                pass
            sig = p.get('patternSig') or "None"
            print(f"{sig:<30} | {name}")
    else:
        print("No list data found or error:", json.dumps(data, ensure_ascii=False)[:200])

    print("\n--- 3. List All Agents (getAllAgent) ---")
    data = make_request("GET", "/getAllAgent", params={"pageNum": 1, "pageSize": 100})
    if data and "data" in data and isinstance(data["data"], dict):
        content = data["data"].get("content", [])
        print(f"Total Agents Found: {data['data'].get('totalElements')}")
        print(f"{'Key':<30} | {'Name':<40} | {'Creator'}")
        print("-" * 100)
        for agent in content:
            name = agent.get('agentName') or "Unknown"
            key = agent.get('agentKey') or "Unknown"
            creator = agent.get('audit', {}).get('createdBy', 'Unknown')
            print(f"{key:<30} | {name:<40} | {creator}")
    else:
        print("Error getting agents:", json.dumps(data, ensure_ascii=False)[:200])

    print("\n--- 4. List Components (getAllComponent) ---")
    data = make_request("GET", "/getAllComponent", params={"pageNum": 1, "pageSize": 10})
    if data and "data" in data and isinstance(data["data"], dict):
        content = data["data"].get("content", [])
        print(f"Total Components Found: {data['data'].get('totalElements')}")
        for item in content:
            name = item.get('componentName') or "Unknown"
            print(f"Component: {name}")
    else:
        print("No component data:", json.dumps(data, ensure_ascii=False)[:200])



