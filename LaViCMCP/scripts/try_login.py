import requests
import json

base_url = "http://192.168.31.218:7980/api/v1/lavic-user"

def try_login(username, password, tenant_id=None):
    url = f"{base_url}/login"
    params = {
        "userName": username,
        "password": password
    }
    if tenant_id:
        params["tenantId"] = tenant_id
        
    print(f"Trying login with {username}/{password}...")
    try:
        resp = requests.post(url, params=params, timeout=5)
        print(f"Status: {resp.status_code}")
        print(resp.text[:200])
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Try common defaults
    try_login("admin", "123456")
    try_login("admin", "admin")
    try_login("user", "123456")
