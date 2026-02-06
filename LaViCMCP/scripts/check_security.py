import json

def check_security(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Security Definitions: {data.get('securityDefinitions')}")
    print(f"Security: {data.get('security')}")

if __name__ == "__main__":
    check_security("docs/core.json")
