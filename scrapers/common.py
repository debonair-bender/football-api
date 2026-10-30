"""Shared Matchesio collector; intended only for permitted automated access."""
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SEASON = "2026/2027"
SEASON_FILE = SEASON.replace("/", "-")
ROOT = Path(__file__).resolve().parents[1]


def parse_match(row):
    def txt(selector):
        el = row.select_one(selector)
        return el.get_text(" ", strip=True) if el else None

    score_text = txt(".score-pill")
    score = re.search(r"(\d+)\s*[-–—]\s*(\d+)", score_text or "")
    timestamp = row.get("data-time")
    round_raw = row.get("data-matchday")
    return {
        "id": row.get("data-match-id"),
        "timestamp": int(timestamp) if timestamp and timestamp.isdigit() else None,
        "date": row.get("data-day"),
        "time": txt(".match-time"),
        "round": int(round_raw) if round_raw and round_raw.isdigit() else None,
        "homeTeam": txt(".match-team-home .team-name") or row.get("data-home"),
        "awayTeam": txt(".match-team-away .team-name") or row.get("data-away"),
        "stadium": row.get("data-venue"),
        "city": row.get("data-city"),
        "status": row.get("data-status"),
        "homeScore": int(score.group(1)) if score else None,
        "awayScore": int(score.group(2)) if score else None,
    }


def collect(*, slug, competition, base_url, expected_matches=None, expected_rounds=None):
    """Crawl pages until source explicitly sets has_next=false.

    Assumes the same JSON + match-row structure confirmed for Serie B.
    It has not yet been verified against Serie A / Champions endpoints.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "FootballCalendarSync/1.0 (automated calendar retrieval)",
        "Accept": "application/json",
    })
    page = 1
    visited = set()
    matches = {}
    # Safety guard against endless traversal; not a page count to configure.
    safety_limit = 1000
    while True:
        if page in visited or len(visited) >= safety_limit:
            raise RuntimeError(f"{slug}: pagination loop or excessive pages")
        visited.add(page)
        response = session.get(base_url, params={"page": page}, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("html"), str):
            raise ValueError(f"{slug}: page {page}: unexpected JSON format")
        soup = BeautifulSoup(data["html"], "html.parser")
        rows = soup.select("tr.match-row[data-match-id]")
        if not rows:
            raise ValueError(f"{slug}: page {page}: no match rows")
        for row in rows:
            m = parse_match(row)
            if not m["id"] or not m["homeTeam"] or not m["awayTeam"] or not m["date"]:
                raise ValueError(f"{slug}: incomplete match on page {page}: {m}")
            if m["id"] in matches and matches[m["id"]] != m:
                raise ValueError(f"{slug}: conflicting duplicate id {m['id']}")
            matches[m["id"]] = m
        print(f"{slug} page {page}: {len(rows)} rows; unique matches: {len(matches)}")
        if data.get("has_next") is False:
            break
        if data.get("has_next") is not True:
            raise ValueError(f"{slug}: page {page}: has_next missing or invalid")
        next_page = data.get("next_page")
        if type(next_page) is not int or next_page <= page:
            raise ValueError(f"{slug}: page {page}: invalid next_page={next_page}")
        page = next_page
        time.sleep(1)

    result_matches = sorted(matches.values(), key=lambda m: (m["timestamp"] or 0, m["id"]))
    if expected_matches is not None and len(result_matches) != expected_matches:
        raise ValueError(f"{slug}: expected {expected_matches} matches; got {len(result_matches)}")
    if expected_rounds is not None:
        counts = Counter(m["round"] for m in result_matches)
        if set(counts) != set(range(1, expected_rounds + 1)):
            raise ValueError(f"{slug}: incomplete rounds: {sorted(counts)}")
    
    # Percorso automatico per competizione e stagione
    output_file = ROOT / "data" / slug / f"{SEASON_FILE}.json"

    # Crea automaticamente le cartelle mancanti
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Evita di riscrivere file con dati identici
    if output_file.exists():
        previous = json.loads(output_file.read_text(encoding="utf-8"))

        if previous.get("matches") == result_matches:
            print(f"{slug}: nessuna modifica")
            return

    result = {
        "competition": competition,
        "season": SEASON,
        "total": len(result_matches),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "matches": result_matches
    }

    # Scrittura temporanea per evitare file incompleti
    temp_file = output_file.with_suffix(".json.tmp")

    temp_file.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    temp_file.replace(output_file)
    print(f"{slug}: salvato {output_file}")
