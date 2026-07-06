#!/usr/bin/env python3
import json
import os
import socket
import sys


def check_blender_mcp(host: str, port: int) -> int:
    print(f"Checking Blender MCP on {host}:{port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect((host, port))
        print("OK: TCP connection established")
    except Exception as exc:
        print(f"FAIL: cannot connect ({exc})")
        return 1

    try:
        payload = {"type": "get_scene_info", "params": {}}
        sock.sendall(json.dumps(payload).encode("utf-8"))
        data = sock.recv(4096)
        if data:
            preview = data.decode("utf-8", errors="replace")[:240]
            print(f"OK: response received: {preview}")
            return 0
        print("WARN: no response payload")
        return 2
    except Exception as exc:
        print(f"WARN: command probe failed ({exc})")
        return 2
    finally:
        sock.close()


def main() -> int:
    host = os.environ.get("BLENDER_MCP_HOST", "127.0.0.1")
    port_text = os.environ.get("BLENDER_MCP_PORT", "9876")
    try:
        port = int(port_text)
    except ValueError:
        print(f"FAIL: invalid BLENDER_MCP_PORT={port_text}")
        return 3
    return check_blender_mcp(host, port)


if __name__ == "__main__":
    sys.exit(main())
