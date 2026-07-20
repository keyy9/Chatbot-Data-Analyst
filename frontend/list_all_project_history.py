import os
import json
from urllib.parse import unquote, urlparse

history_path = r"C:\Users\Lenovo\AppData\Roaming\Code\User\History"

for root, dirs, files in os.walk(history_path):
    entries_file = os.path.join(root, "entries.json")
    if not os.path.exists(entries_file):
        continue
        
    try:
        with open(entries_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        resource_url = data.get("resource", "")
        if "lapis" in resource_url.lower():
            print(f"Folder: {os.path.basename(root)} -> Resource: {resource_url}")
            for entry in data.get("entries", []):
                print(f"  Version: {entry.get('id')} at {entry.get('timestamp')}")
    except Exception as e:
        pass
