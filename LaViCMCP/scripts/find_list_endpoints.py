import json

def find_list_endpoints(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    paths = data.get('paths', {})
    list_endpoints = []
    
    for path, methods in paths.items():
        for method, details in methods.items():
            params = details.get('parameters', [])
            has_page = False
            for param in params:
                if param.get('name') == 'pageNum':
                    has_page = True
                    break
            
            if has_page:
                list_endpoints.append(f"{method.upper()} {path} - {details.get('summary', 'No summary')}")
                
    for ep in list_endpoints:
        print(ep)

if __name__ == "__main__":
    print("--- Core Endpoints with Pagination ---")
    find_list_endpoints("docs/core.json")
