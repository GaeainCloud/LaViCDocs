#!/usr/bin/env python3
import os
from typing import Tuple

import requests
from dotenv import load_dotenv


def normalize_token(token: str) -> Tuple[str, str]:
    token = (token or "").strip()
    if token.startswith("admin-Token="):
        raw = token.split("=", 1)[1].strip()
        return raw, token
    return token, (f"admin-Token={token}" if token else "")


def main() -> int:
    load_dotenv()
    base_url = os.getenv(
        "LAVIC_API_BASE_URL",
        "http://192.168.31.218:7980/api/v1/lavic-core",
    ).strip()
    user_id = os.getenv("LAVIC_USER_ID", "").strip()
    token = os.getenv("LAVIC_API_TOKEN", "").strip()

    missing = []
    if not user_id:
        missing.append("LAVIC_USER_ID")
    if not token:
        missing.append("LAVIC_API_TOKEN")

    if missing:
        print(f"[FAIL] Missing env vars: {', '.join(missing)}")
        return 1

    raw_token, auth_token = normalize_token(token)
    headers = {
        "X-UserId": user_id,
        "Authorization": auth_token,
        "X-token": raw_token,
    }

    checks = [
        ("models", "/getAllAgent", {"pageNum": 1, "pageSize": 1}),
        ("scenarios", "/getAllSysOfSysStep", {"pageNum": 1, "pageSize": 1, "simulationTag": 1}),
    ]

    failed = 0
    for name, path, params in checks:
        try:
            resp = requests.get(f"{base_url}{path}", headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            body = resp.json()
            code = body.get("code")
            ok = code == 200
            print(f"[{'OK' if ok else 'FAIL'}] {name}: http={resp.status_code}, code={code}")
            if not ok:
                failed += 1
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {name}: {exc}")

    if failed:
        print("[RESULT] Self-check failed.")
        return 2

    print("[RESULT] Self-check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
