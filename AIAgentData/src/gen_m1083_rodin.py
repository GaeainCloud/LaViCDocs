import requests
import json
import time
import os

API_KEY = "k9TcfFoEhNd9cCPP2guHAHHHkctZHIRhZDywZ1euGUXwihbYLpOjQhofby80NJez"
IMAGE_PATH = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\downloads\M1083_A1P2_Truck.png"
OUTPUT_GLB = r"d:\AIProduct\GaeainCloud\LaViCDocs\AIAgentData\models\downloads\M1083_A1P2_Truck_AI_Rodin.glb"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "User-Agent": "blender-mcp"
}

def create_job():
    print("Creating Rodin job...")
    if not os.path.exists(IMAGE_PATH):
        print(f"Image not found: {IMAGE_PATH}")
        return None, None

    files = [
        ("images", ("0000.png", open(IMAGE_PATH, "rb"))),
        ("tier", (None, "Sketch")),
        ("mesh_mode", (None, "Raw")),
        ("prompt", (None, "M1083 A1P2 Truck, military cargo truck, high quality, realistic, 3d asset"))
    ]
    
    try:
        response = requests.post(
            "https://hyperhuman.deemos.com/api/v2/rodin",
            headers=HEADERS,
            files=files
        )
        print(f"Create response: {response.status_code} - {response.text}")
        if response.status_code in [200, 201]:
            data = response.json()
            sub_key = None
            task_uuid = data.get("uuid")
            
            if "jobs" in data and "subscription_key" in data["jobs"]:
                sub_key = data["jobs"]["subscription_key"]
            else:
                sub_key = data.get("subscription_key")
                
            return sub_key, task_uuid
        return None, None
    except Exception as e:
        print(f"Error creating job: {e}")
        return None, None

def poll_job(subscription_key):
    print(f"Polling job {subscription_key}...")
    while True:
        try:
            response = requests.post(
                "https://hyperhuman.deemos.com/api/v2/status",
                headers=HEADERS,
                json={"subscription_key": subscription_key}
            )
            if response.status_code not in [200, 201]:
                print(f"Poll failed: {response.status_code}")
                time.sleep(5)
                continue
            
            data = response.json()
            if "jobs" not in data or not data["jobs"]:
                print("No jobs found in status.")
                return False
            
            statuses = [j["status"] for j in data["jobs"]]
            print(f"Statuses: {statuses}")
            
            if all(s == "Done" for s in statuses):
                return True
            
            if any(s == "Failed" for s in statuses):
                print("Job failed.")
                return False
                
            time.sleep(5)
        except Exception as e:
            print(f"Error polling: {e}")
            time.sleep(5)

def download_asset(task_uuid):
    print(f"Downloading asset {task_uuid}...")
    try:
        response = requests.post(
            "https://hyperhuman.deemos.com/api/v2/download",
            headers=HEADERS,
            json={'task_uuid': task_uuid}
        )
        if response.status_code != 200:
            print(f"Download init failed: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        glb_url = None
        for item in data.get("list", []):
            if item["name"].endswith(".glb"):
                glb_url = item["url"]
                break
        
        if not glb_url:
            print("No GLB found in download list.")
            return False
            
        print(f"Downloading GLB from {glb_url}...")
        glb_resp = requests.get(glb_url, stream=True)
        if glb_resp.status_code == 200:
            with open(OUTPUT_GLB, 'wb') as f:
                for chunk in glb_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Saved to {OUTPUT_GLB}")
            return True
        else:
            print(f"GLB download failed: {glb_resp.status_code}")
            return False
            
    except Exception as e:
        print(f"Error downloading: {e}")
        return False

if __name__ == "__main__":
    sub_key, task_uuid = create_job()
    if sub_key and task_uuid:
        if poll_job(sub_key):
            download_asset(task_uuid)
