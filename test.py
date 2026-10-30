import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Configurazione
BASE_URL = "https://www.matchesio.com/it/competition/serie-b-it/matches/"
OUTPUT_FILE = Path("serie-b.json")
SEASON = "2026/2027"
EXPECTED_MATCHES = 380
EXPECTED_ROUNDS = 38
MAX_PAGES = 30

session = requests.Session()
session.headers.update({
    "User-Agent": "SerieBCalendarSync/1.0",
    "Accept": "application/json",
})


def parse_match(row):
    def get_text(selector):
        element = row.select_one(selector)
        return element.get_text(" ", strip=True) if element else None

    score_text = get_text(".score-pill")
    score = re.search(r"(\d+)\s*[-–]\s*(\d+)", score_text) if score_text else None

    return {
        "id": row.get("data-match-id"),
        "timestamp": int(row.get("data-time", 0)),
        "date": row.get("data-day"),
        "time": get_text(".match-time"),
        "round": int(row.get("data-matchday", 0)),
        "homeTeam": get_text(".match-team-home .team-name"),
        "awayTeam": get_text(".match-team-away .team-name"),
        "stadium": row.get("data-venue"),
        "city": row.get("data-city"),
        "status": row.get("data-status"),
        "homeScore": int(score.group(1)) if score else None,
        "awayScore": int(score.group(2)) if score else None,
    }


def fetch_page(page):
    response = session.get(BASE_URL, params={"page": page}, timeout=30)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict) or not isinstance(data.get("html"), str):
        raise ValueError("Risposta JSON non valida")

    soup = BeautifulSoup(data["html"], "html.parser")
    rows = soup.select("tr.match-row[data-match-id]")
    matches = [parse_match(row) for row in rows]
    print(f"Pagina {page}: {len(matches)} partite")
    return matches, data


def validate_matches(matches):
    if len(matches) != EXPECTED_MATCHES:
        raise ValueError(f"Partite incomplete: {len(matches)}/{EXPECTED_MATCHES}")

    ids = [m["id"] for m in matches]
    if len(set(ids)) != len(ids):
        raise ValueError("Trovati ID duplicati")

    rounds = Counter(m["round"] for m in matches)
    if set(rounds) != set(range(1, EXPECTED_ROUNDS + 1)):
        raise ValueError("Giornate mancanti o non valide")
    if any(count != 10 for count in rounds.values()):
        raise ValueError("Numero partite per giornata non valido")

    for match in matches:
        required = ["id", "timestamp", "date", "round", "homeTeam", "awayTeam", "status"]
        if any(not match.get(field) for field in required):
            raise ValueError(f"Dati obbligatori mancanti: {match}")
        if match["homeTeam"] == match["awayTeam"]:
            raise ValueError(f"Squadre identiche nella partita {match['id']}")


def main():
    matches_by_id = {}
    page = 1
    visited_pages = set()

    while page is not None:
        if page in visited_pages or len(visited_pages) >= MAX_PAGES:
            raise RuntimeError("Paginazione non valida")
        visited_pages.add(page)
        page_matches, data = fetch_page(page)
        if not page_matches:
            raise RuntimeError(f"Pagina {page} senza partite")
        for match in page_matches:
            matches_by_id[match["id"]] = match

        if data.get("has_next") is True:
            next_page = data.get("next_page")
            if not isinstance(next_page, int) or next_page <= page:
                raise RuntimeError("next_page non valido")
            page = next_page
            time.sleep(1)
        else:
            page = None

    matches = sorted(matches_by_id.values(), key=lambda m: (m["timestamp"], m["id"]))
    validate_matches(matches)
    print(f"Totale partite: {len(matches)}")
    print(f"Giornate: {len(set(m['round'] for m in matches))}")
    print(f"Partite giocate: {sum(m['status'] == 'GIOCATA' for m in matches)}")

    if OUTPUT_FILE.exists():
        previous = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        if previous.get("matches") == matches:
            print("Nessuna modifica. JSON già aggiornato.")
            return

    result = {
        "competition": "Serie B",
        "season": SEASON,
        "total": len(matches),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "matches": matches,
    }
    temp_file = OUTPUT_FILE.with_suffix(".json.tmp")
    temp_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_file.replace(OUTPUT_FILE)
    print(f"File aggiornato: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
