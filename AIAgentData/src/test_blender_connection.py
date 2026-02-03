import socket
import json
import time

def test_connection():
    HOST = '127.0.0.1'
    PORT = 9876  # Default BlenderMCP port
    
    print(f"Testing connection to Blender MCP at {HOST}:{PORT}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((HOST, PORT))
            print("✅ TCP Connection Successful!")
            
            # Try sending a ping/info command
            cmd = {
                "type": "get_scene_info",
                "params": {}
            }
            print("Sending 'get_scene_info' command...")
            s.sendall(json.dumps(cmd).encode('utf-8'))
            
            data = s.recv(4096)
            if data:
                print(f"✅ Received Response: {data.decode('utf-8')[:200]}...")
            else:
                print("⚠️ Connected but received no data.")
                
            return True
            
    except ConnectionRefusedError:
        print("❌ Connection Refused!")
        print("Possible causes:")
        print("1. Blender is not running.")
        print("2. Blender MCP Addon is not installed or enabled.")
        print("3. The Server is not started (Check Sidebar > BlenderMCP > Connect).")
        print("4. Port mismatch (Default is 9876).")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
import socket

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

ports = [9876, 7986]
for p in ports:
    if check_port(p):
        print(f"Port {p} is OPEN")
    else:
        print(f"Port {p} is CLOSED")
