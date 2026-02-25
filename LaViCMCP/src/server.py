import asyncio
import json
import logging
import os
import time
import requests
from typing import Optional, List, Any
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lavic-mcp")

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("LAVIC_API_BASE_URL", "http://192.168.31.218:7980/api/v1/lavic-core")
DEFAULT_USER_ID = os.getenv("LAVIC_USER_ID", "")
API_TOKEN = os.getenv("LAVIC_API_TOKEN", "")

app = Server("lavic-mcp")

def normalize_token(token: str) -> tuple[str, str]:
    """
    Return both raw JWT and Authorization header value.
    Accepts either:
    - <jwt>
    - admin-Token=<jwt>
    """
    token = (token or "").strip()
    if token.startswith("admin-Token="):
        raw = token.split("=", 1)[1].strip()
        return raw, token
    return token, (f"admin-Token={token}" if token else "")

def validate_runtime_config() -> list[str]:
    """
    Validate required runtime configuration.
    Returns a list of validation errors.
    """
    errors: list[str] = []
    if not API_BASE_URL:
        errors.append("LAVIC_API_BASE_URL is required")
    if not DEFAULT_USER_ID:
        errors.append("LAVIC_USER_ID is required")
    if not API_TOKEN:
        errors.append("LAVIC_API_TOKEN is required")
    return errors

def make_request(
    method: str,
    endpoint: str,
    params: dict = None,
    json_data: dict = None,
    user_id: str = None,
    return_raw: bool = False,
    timeout: int = 30,
    retries: int = 1,
    backoff_seconds: float = 0.5,
) -> Any:
    """
    通用 API 请求函数
    """
    url = f"{API_BASE_URL}{endpoint}"
    raw_token, auth_token = normalize_token(API_TOKEN)
    # Compatibility headers:
    # - Authorization: admin-Token=<token>
    # - X-token: <token>
    headers = {
        "X-UserId": user_id or DEFAULT_USER_ID,
        "Content-Type": "application/json",
        "Authorization": auth_token,
        "X-token": raw_token,
    }
    
    for attempt in range(retries + 1):
        try:
            response = requests.request(
                method,
                url,
                params=params,
                json=json_data,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            if return_raw:
                return response

            # Handle SSE (Server-Sent Events) responses
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                for line in response.text.splitlines():
                    if line.startswith("data:"):
                        try:
                            return json.loads(line[5:])
                        except json.JSONDecodeError:
                            pass

            # Default JSON handling
            try:
                return response.json()
            except json.JSONDecodeError:
                # If not JSON and not handled SSE, return text or empty dict
                if response.text.strip():
                    return {"message": response.text}
                return {}

        except requests.exceptions.RequestException as e:
            is_last = attempt >= retries
            if not is_last:
                time.sleep(backoff_seconds * (attempt + 1))
                continue
            error_msg = str(e)
            status_code = getattr(e.response, "status_code", None)
            try:
                error_body = e.response.json() if e.response else None
            except Exception:
                error_body = e.response.text if e.response else None

            return {
                "error": error_msg,
                "status_code": status_code,
                "details": error_body,
            }

def get_running_record_sig(sim_id: str, user_id: str = None) -> Optional[str]:
    """
    Find the running record signature for a simulation.
    Returns the recordSig if found, None otherwise.
    """
    try:
        # Get records for this simulation
        params = {"simulationSig": sim_id, "pageNum": 1, "pageSize": 20}
        result = make_request("GET", "/getAllRecord", params=params, user_id=user_id)
        
        if result and "data" in result and "content" in result["data"]:
            records = result["data"]["content"]
            # Look for running status
            for record in records:
                status = record.get("recordStatus")
                # Check for various forms of "Running" status just in case
                if status in ["Running", "running", 1, "1"]: 
                    return record.get("recordSig")
            
            # If no running record found, but there are records, 
            # maybe return the latest one if we want to be aggressive? 
            # But safer to return None if strictly looking for running.
            pass
            
    except Exception as e:
        logger.error(f"Error finding running record: {e}")
        
    return None

@app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="list_scenarios",
            description="Query scenario (simulation) list with pagination. Set fetch_all=True to retrieve all items.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "Page number (default 1)", "default": 1},
                    "size": {"type": "integer", "description": "Page size (default 10)", "default": 10},
                    "fetch_all": {"type": "boolean", "description": "If true, fetches all pages. Overrides page/size.", "default": False},
                    "simulation_tag": {"type": "string", "description": "Filter by simulation tag (Integer). Default '1' for System/Admin Scenarios (including MicroScenarios). Pass empty string for User Scenarios.", "default": "1"},
                    "user_id": {"type": "string", "description": "Optional User ID override"}
                }
            },
        ),
        Tool(
            name="list_models",
            description="List available simulation models (agents). Use keyword to search. Set is_model_case=True to filter for 'Model Cases' (模型案例). Set fetch_all=True to retrieve all items.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Search keyword for model name"},
                    "page": {"type": "integer", "default": 1, "description": "Page number (default 1)"},
                    "size": {"type": "integer", "default": 10, "description": "Page size (default 10)"},
                    "fetch_all": {"type": "boolean", "default": False, "description": "If true, fetches all pages. Overrides page/size."},
                    "is_model_case": {"type": "boolean", "default": False, "description": "If true, filters for 'Model Cases' (agentTag=1)."},
                    "user_id": {"type": "string", "description": "Optional User ID override"}
                }
            },
        ),
        Tool(
            name="control_scenario",
            description="Control scenario execution (start, pause, resume, stop).",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string", 
                        "enum": ["start", "pause", "resume", "stop"],
                        "description": "Action to perform"
                    },
                    "simulation_id": {"type": "string", "description": "Simulation ID"},
                    "record_id": {"type": "string", "description": "Record ID (required for pause/resume/stop if available)"},
                    "user_id": {"type": "string", "description": "Optional User ID override"}
                },
                "required": ["action", "simulation_id"]
            },
        ),
        Tool(
            name="download_record_data",
            description="Download and extract CSV data for a specific simulation record.",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {"type": "string", "description": "Record ID (recordSig)"},
                    "output_dir": {"type": "string", "description": "Directory to save data (optional, defaults to ./data/<record_id>)"},
                    "user_id": {"type": "string", "description": "Optional User ID override"}
                },
                "required": ["record_id"]
            },
        ),
        Tool(
            name="set_simulation_speed",
            description="Set running simulation speed multiplier via engine progress control.",
            inputSchema={
                "type": "object",
                "properties": {
                    "simulation_id": {"type": "string", "description": "Simulation ID"},
                    "speed": {"type": "integer", "description": "Speed multiplier, e.g. 10 for 10x"},
                    "record_id": {"type": "string", "description": "Optional running record ID (recordSig). If omitted, it will auto-detect."},
                    "user_id": {"type": "string", "description": "Optional User ID override"},
                    "timeout_seconds": {"type": "integer", "description": "Request timeout for engine control API", "default": 20}
                },
                "required": ["simulation_id", "speed"]
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    if name == "list_scenarios":
        page = arguments.get("page", 1)
        size = arguments.get("size", 10)
        fetch_all = arguments.get("fetch_all", False)
        user_id = arguments.get("user_id")
        simulation_tag = arguments.get("simulation_tag", "1")
        
        params = {"pageNum": page, "pageSize": size}
        if simulation_tag is not None and str(simulation_tag) != "":
            params["simulationTag"] = simulation_tag
            
        if fetch_all:
            all_content = []
            current_page = 1
            params["pageSize"] = 50 # Use larger batch for efficiency
            
            while True:
                params["pageNum"] = current_page
                result = make_request("GET", "/getAllSysOfSysStep", params=params, user_id=user_id)
                
                if not result or result.get("code") != 200:
                    return [TextContent(type="text", text=json.dumps({
                        "success": False,
                        "message": "Failed while fetching paginated scenarios.",
                        "page": current_page,
                        "last_response": result,
                        "partial_count": len(all_content)
                    }, ensure_ascii=False, indent=2))]
                    
                data = result.get("data", {})
                content = data.get("content", [])
                all_content.extend(content)
                
                if current_page >= data.get("totalPages", 0):
                    break
                current_page += 1
                
            return [TextContent(type="text", text=json.dumps({
                "code": 200,
                "message": "Fetched all items",
                "data": {
                    "content": all_content,
                    "totalElements": len(all_content)
                }
            }, ensure_ascii=False, indent=2))]
        else:
            result = make_request("GET", "/getAllSysOfSysStep", params=params, user_id=user_id)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "list_models":
        keyword = arguments.get("keyword")
        page = arguments.get("page", 1)
        size = arguments.get("size", 10)
        fetch_all = arguments.get("fetch_all", False)
        is_model_case = arguments.get("is_model_case", False)
        user_id = arguments.get("user_id")

        params = {
            "pageNum": page,
            "pageSize": size
        }
        if keyword:
            params["agentKwd"] = keyword
        
        if is_model_case:
            params["agentTag"] = 1
            
        if fetch_all:
            all_content = []
            current_page = 1
            params["pageSize"] = 50
            
            while True:
                params["pageNum"] = current_page
                result = make_request("GET", "/getAllAgent", params=params, user_id=user_id)
                
                if not result or result.get("code") != 200:
                    return [TextContent(type="text", text=json.dumps({
                        "success": False,
                        "message": "Failed while fetching paginated models.",
                        "page": current_page,
                        "last_response": result,
                        "partial_count": len(all_content)
                    }, ensure_ascii=False, indent=2))]
                    
                data = result.get("data", {})
                content = data.get("content", [])
                all_content.extend(content)
                
                if current_page >= data.get("totalPages", 0):
                    break
                current_page += 1
            
            return [TextContent(type="text", text=json.dumps({
                "code": 200,
                "message": "Fetched all items",
                "data": {
                    "content": all_content,
                    "totalElements": len(all_content)
                }
            }, ensure_ascii=False, indent=2))]
        else:
            # Use /getAllAgent for models
            result = make_request("GET", "/getAllAgent", params=params, user_id=user_id)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "control_scenario":
        action = arguments.get("action")
        sim_id = arguments.get("simulation_id")
        record_id = arguments.get("record_id")
        user_id = arguments.get("user_id")
        
        result = {}
        if action == "start":
            # StartParam structure
            # startType must be "simulation" (based on testing and user feedback)
            payload = {
                "simulationId": sim_id,
                "startType": "simulation" 
            }
            result = make_request("POST", "/startSimulation", json_data=payload, user_id=user_id)
            
        elif action in ["pause", "resume", "stop"]:
            # If record_id is not provided, try to find the running record
            if not record_id:
                record_id = get_running_record_sig(sim_id, user_id)
                if not record_id:
                    return [TextContent(type="text", text=json.dumps({
                        "success": False, 
                        "message": f"No running record found for simulation {sim_id}. Please provide record_id explicitly if needed."
                    }, ensure_ascii=False, indent=2))]

            if action == "stop":
                # StopParam structure
                payload = {
                    "isStopAll": False,
                    "recordSig": record_id,
                    "configId": None
                }
                result = make_request("POST", "/stopSimulation", json_data=payload, user_id=user_id)
            else:
                # Pause/Resume use CtrlParam
                payload = {
                    "ctrlDoe": False,
                    "recordSig": record_id
                }
                endpoint_map = {
                    "pause": "/pauseSimulation",
                    "resume": "/resumeSimulation"
                }
                result = make_request("POST", endpoint_map[action], json_data=payload, user_id=user_id)
            
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "download_record_data":
        record_id = arguments.get("record_id")
        output_dir = arguments.get("output_dir") or f"./data/{record_id}"
        user_id = arguments.get("user_id")
        
        # Make request with raw response
        try:
            result = make_request(
                "POST",
                "/getRecordData",
                params={"recordSig": record_id},
                user_id=user_id,
                return_raw=True,
                timeout=120,
                retries=2,
            )
            
            # Check if it's an error dict (from exception handler in make_request)
            if isinstance(result, dict) and "error" in result:
                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
            
            # result is the response object
            import zipfile
            import io
            
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            try:
                with zipfile.ZipFile(io.BytesIO(result.content)) as z:
                    z.extractall(output_dir)
                    file_list = z.namelist()
                    
                return [TextContent(type="text", text=json.dumps({
                    "success": True,
                    "message": f"Data downloaded and extracted to {output_dir}",
                    "files": file_list,
                    "local_path": os.path.abspath(output_dir)
                }, ensure_ascii=False, indent=2))]
                
            except zipfile.BadZipFile:
                return [TextContent(type="text", text=json.dumps({
                    "success": False, 
                    "message": "Response was not a valid ZIP file."
                }, ensure_ascii=False, indent=2))]
                
        except Exception as e:
             return [TextContent(type="text", text=json.dumps({
                "success": False, 
                "error": str(e)
            }, ensure_ascii=False, indent=2))]

    elif name == "set_simulation_speed":
        sim_id = arguments.get("simulation_id")
        speed = arguments.get("speed")
        record_id = arguments.get("record_id")
        user_id = arguments.get("user_id")
        timeout_seconds = arguments.get("timeout_seconds", 20)

        try:
            speed_int = int(speed)
            if speed_int <= 0:
                raise ValueError("speed must be > 0")
        except Exception:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Invalid speed: {speed}. It must be a positive integer."
            }, ensure_ascii=False, indent=2))]

        if not record_id:
            record_id = get_running_record_sig(sim_id, user_id)
            if not record_id:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "message": f"No running record found for simulation {sim_id}. Please provide record_id explicitly."
                }, ensure_ascii=False, indent=2))]

        payload = {
            "ctrltype": "prgctrl",
            "ctrlparam": str(speed_int),
            "recordSig": record_id,
            "simid": sim_id,
        }

        result = make_request(
            "POST",
            "/progressCtrl",
            json_data=payload,
            user_id=user_id,
            timeout=int(timeout_seconds),
        )
        return [TextContent(type="text", text=json.dumps({
            "success": result.get("success", False) if isinstance(result, dict) else False,
            "request": payload,
            "response": result
        }, ensure_ascii=False, indent=2))]

    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    errors = validate_runtime_config()
    if errors:
        logger.error("Invalid runtime configuration: %s", "; ".join(errors))
        raise RuntimeError("Invalid runtime configuration. Please check .env values.")
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
