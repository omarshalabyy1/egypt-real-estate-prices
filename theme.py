"""Write the client's title and colours from config/client.yaml into powerbi/05-theme.json."""

import json
from pathlib import Path

from config import load_config

cfg = load_config()
c = cfg["report"]["colours"]
path = Path(__file__).parent / "powerbi" / "05-theme.json"
theme = json.loads(path.read_text(encoding="utf-8"))

theme["name"] = cfg["report"]["title"]
theme["dataColors"] = c["data"]
theme["foreground"] = c["text"]
theme["tableAccent"] = theme["good"] = theme["maximum"] = c["data"][0]
theme["center"] = c["data"][2]
theme["neutral"] = c["muted"]
theme["bad"] = c["danger"]
for name, text_class in theme["textClasses"].items():
    text_class["color"] = c["muted"] if name == "label" else c["text"]
theme["visualStyles"]["*"]["*"]["border"][0]["color"]["solid"]["color"] = c["line"]
theme["visualStyles"]["page"]["*"]["background"][0]["color"]["solid"]["color"] = c["page"]

path.write_text(json.dumps(theme, indent=2) + "\n", encoding="utf-8")
print(f"wrote {path.name}: {theme['name']}, main colour {c['data'][0]}")
