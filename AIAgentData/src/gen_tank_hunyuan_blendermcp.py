#!/usr/bin/env python3
"""
Generate a tank model via BlenderMCP + Hunyuan3D and export to GLB.

Usage example:
  python src/gen_tank_hunyuan_blendermcp.py
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path
from typing import Any


def _walk_json(value: Any):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k, v
            yield from _walk_json(v)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)


def _extract_first_key(data: Any, key_candidates: set[str]) -> Any | None:
    lowered = {k.lower() for k in key_candidates}
    for key, value in _walk_json(data):
        if isinstance(key, str) and key.lower() in lowered:
            return value
    return None


def _collect_urls(data: Any) -> list[str]:
    urls: list[str] = []
    for _, value in _walk_json(data):
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            urls.append(value)
    return urls


class BlenderMCPClient:
    def __init__(self, host: str, port: int, timeout_sec: int = 180):
        self.host = host
        self.port = port
        self.timeout_sec = timeout_sec
        self.sock: socket.socket | None = None

    def __enter__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout_sec)
        sock.connect((self.host, self.port))
        self.sock = sock
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    def call(self, cmd_type: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.sock:
            raise RuntimeError("MCP socket is not connected")
        payload = json.dumps({"type": cmd_type, "params": params or {}}).encode("utf-8")
        self.sock.sendall(payload)
        return self._recv_json()

    def _recv_json(self) -> dict[str, Any]:
        if not self.sock:
            raise RuntimeError("MCP socket is not connected")
        start = time.time()
        buf = b""
        while True:
            if time.time() - start > self.timeout_sec:
                raise TimeoutError("Timed out waiting for BlenderMCP response")
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("BlenderMCP socket closed before response")
            buf += chunk
            try:
                return json.loads(buf.decode("utf-8"))
            except json.JSONDecodeError:
                continue


def _require_success(resp: dict[str, Any], cmd_name: str) -> Any:
    if resp.get("status") != "success":
        raise RuntimeError(f"{cmd_name} failed: {resp}")
    return resp.get("result")


def _wait_hunyuan_done(
    client: BlenderMCPClient, job_id: str, poll_interval_sec: int, max_polls: int
) -> dict[str, Any]:
    done_states = {"DONE", "SUCCEEDED", "SUCCESS", "FINISHED", "COMPLETED"}
    fail_states = {"FAILED", "FAIL", "ERROR", "CANCELLED", "CANCELED"}

    for i in range(1, max_polls + 1):
        poll = client.call("poll_hunyuan_job_status", {"job_id": job_id})
        result = _require_success(poll, "poll_hunyuan_job_status")
        maybe_error = _extract_first_key(result, {"error", "message"})
        if isinstance(maybe_error, str) and maybe_error.lower().startswith("error"):
            raise RuntimeError(f"Hunyuan poll error: {result}")

        status = _extract_first_key(
            result,
            {"status", "jobstatus", "job_status", "jobstatuscode", "state"},
        )
        status_text = str(status).upper() if status is not None else "UNKNOWN"
        print(f"[poll {i}/{max_polls}] job={job_id} status={status_text}")

        if status_text in done_states:
            return result
        if status_text in fail_states:
            raise RuntimeError(f"Hunyuan job failed: {result}")

        time.sleep(poll_interval_sec)
    raise TimeoutError(f"Hunyuan job did not finish after {max_polls} polls")


def _clear_scene(client: BlenderMCPClient) -> None:
    code = r"""
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for obj in list(bpy.data.objects):
    if obj.users == 0:
        bpy.data.objects.remove(obj)
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
print("scene_cleared")
"""
    resp = client.call("execute_code", {"code": code})
    _require_success(resp, "execute_code(clear_scene)")


def _export_glb(client: BlenderMCPClient, model_name: str, output_glb: Path) -> None:
    # Keep script compact and version-tolerant for Blender 3.x/4.x.
    code = f"""
import bpy
import os
import mathutils

model_name = {model_name!r}
output_path = {str(output_glb)!r}

mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not mesh_objs:
    raise RuntimeError("No mesh object found in scene after import")

bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objs:
    obj.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
if len(mesh_objs) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
obj.name = model_name

# Normalize transform and place model on ground.
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bbox_world = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
min_z = min(v.z for v in bbox_world)
obj.location.x = 0.0
obj.location.y = 0.0
obj.location.z -= min_z
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# Remove cameras/lights to keep exported file clean.
for o in list(bpy.context.scene.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o, do_unlink=True)

os.makedirs(os.path.dirname(output_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB', export_yup=True)
print(output_path)
"""
    resp = client.call("execute_code", {"code": code})
    _require_success(resp, "execute_code(export_glb)")


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parents[1]
    default_image = (
        base
        / "models"
        / "Type99_Main_Battle_Tank"
        / "Type99_Main_Battle_Tank"
        / "Type99_Main_Battle_Tank.png"
    )
    default_output = (
        base
        / "models"
        / "Type99_Main_Battle_Tank"
        / "Type99_Main_Battle_Tank"
        / "Type99_Main_Battle_Tank_AI_Rodin.glb"
    )

    parser = argparse.ArgumentParser(
        description="Generate a tank GLB by calling BlenderMCP Hunyuan3D handlers."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--image", default=str(default_image), help="Reference image path or URL.")
    parser.add_argument("--prompt", default=None, help="Text prompt (exclusive with --image).")
    parser.add_argument("--model-name", default="Type99_Main_Battle_Tank")
    parser.add_argument("--output-glb", default=str(default_output))
    parser.add_argument("--poll-interval-sec", type=int, default=15)
    parser.add_argument("--max-polls", type=int, default=40)
    parser.add_argument(
        "--no-clear-scene",
        action="store_true",
        help="Skip scene cleanup before generation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.image and args.prompt:
        raise ValueError("--image and --prompt cannot be used together")
    if not args.image and not args.prompt:
        raise ValueError("Either --image or --prompt must be provided")

    output_glb = Path(args.output_glb).expanduser().resolve()
    image_value = args.image
    if image_value and not image_value.startswith(("http://", "https://")):
        image_path = Path(image_value).expanduser().resolve()
        if not image_path.exists():
            raise FileNotFoundError(f"Reference image not found: {image_path}")
        image_value = str(image_path)

    try:
        with BlenderMCPClient(args.host, args.port) as client:
            scene_info = _require_success(client.call("get_scene_info"), "get_scene_info")
            print(
                f"Connected to BlenderMCP: scene={scene_info.get('name')} objects={scene_info.get('object_count')}"
            )

            hunyuan_status = _require_success(
                client.call("get_hunyuan3d_status"), "get_hunyuan3d_status"
            )
            if not hunyuan_status.get("enabled"):
                raise RuntimeError(f"Hunyuan3D is not enabled in BlenderMCP: {hunyuan_status}")

            if not args.no_clear_scene:
                _clear_scene(client)

            create_params: dict[str, Any] = {}
            if args.prompt:
                create_params["text_prompt"] = args.prompt
            else:
                create_params["image"] = image_value

            create_result = _require_success(
                client.call("create_hunyuan_job", create_params), "create_hunyuan_job"
            )
            create_error = _extract_first_key(create_result, {"error"})
            if create_error:
                raise RuntimeError(f"Hunyuan create job error: {create_result}")

            job_id = _extract_first_key(create_result, {"JobId", "job_id"})

            poll_result: dict[str, Any] | None = None
            if job_id:
                print(f"Hunyuan job submitted: job_id={job_id}")
                poll_result = _wait_hunyuan_done(
                    client, str(job_id), args.poll_interval_sec, args.max_polls
                )
            else:
                # LOCAL_API mode may finish and import directly without async job id.
                print("No job_id returned; assuming LOCAL_API immediate generation/import.")
                poll_result = create_result

            urls = _collect_urls(poll_result)
            zip_urls = [u for u in urls if ".zip" in u.lower()]
            zip_url = zip_urls[0] if zip_urls else (urls[0] if urls else None)
            if zip_url:
                print(f"Importing generated asset from: {zip_url}")
                import_result = _require_success(
                    client.call(
                        "import_generated_asset_hunyuan",
                        {"name": args.model_name, "zip_file_url": zip_url},
                    ),
                    "import_generated_asset_hunyuan",
                )
                import_error = _extract_first_key(import_result, {"error"})
                if import_error:
                    raise RuntimeError(f"Hunyuan import error: {import_result}")
            else:
                print("No downloadable URL found in poll result; skipping import step.")

            _export_glb(client, args.model_name, output_glb)
    except ConnectionRefusedError:
        print(
            "Cannot connect to BlenderMCP. Start Blender, enable BlenderMCP addon, "
            "enable Hunyuan3D, then click 'Connect to MCP server'."
        )
        return 2
    except Exception as e:
        print(f"Generation failed: {e}")
        return 1

    if output_glb.exists() and output_glb.stat().st_size > 0:
        print(f"Done. GLB exported: {output_glb}")
        return 0
    print(f"Generation reported success but output file missing: {output_glb}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
