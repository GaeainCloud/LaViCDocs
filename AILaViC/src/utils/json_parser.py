import json
import re

def extract_json(text: str) -> dict:
    """
    Robust JSON extractor.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {}
