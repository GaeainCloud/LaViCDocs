import json
from server import make_request

def main():
    print("Fetching all LaViC Scenario Cases (simulationTag=1)...")
    try:
        data = make_request("GET", "/getAllSysOfSysStep", params={"pageNum": 1, "pageSize": 100, "simulationTag": "1"})
        
        if data and "data" in data:
            content = data["data"].get("content", [])
            print(f"\nFound {data['data'].get('totalElements')} scenarios:\n")
            print(f"{'ID':<30} | {'Name'}")
            print("-" * 60)
            for item in content:
                print(f"{item.get('simulationSig'):<30} | {item.get('simulationName')}")
        else:
            print("No data found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
