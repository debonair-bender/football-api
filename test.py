import json
from datetime import datetime, timezone

data = {
    "competition": "Serie B",
    "season": "2026/2027",
    "updatedAt": datetime.now(timezone.utc).isoformat(),
    "message": "GitHub Actions funziona!"
}

with open("serie-b.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("JSON generato correttamente!")
