import json

def search_paths(filepath, keyword):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Searching paths in {filepath} for '{keyword}'...")
    for path, methods in data['paths'].items():
        if keyword.lower() in path.lower():
            for method, details in methods.items():
                print(f"[{method.upper()}] {path}")
                print(f"  Summary: {details.get('summary')}")
                print("  Parameters:")
                for param in details.get('parameters', []):
                    print(f"    - {param['name']} ({param['in']})")

if __name__ == "__main__":
    search_paths("docs/user.json", "login")
