import json

json_path = r'd:\AIProduct\GaeainCloud\LaViCDocs\AILaViC\knowledge_base\examples\想定_防空反导-v1.60.9-修复版\simulation.json'

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

patterns = data[0].get('agentRunningPatterns', [])

def check_none(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            check_none(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            check_none(item, f"{path}[{i}]")
    elif obj is None:
        print(f"[FOUND NONE] {path} is None")

print("Checking agentRunningPatterns for None values...")
check_none(patterns, "agentRunningPatterns")
