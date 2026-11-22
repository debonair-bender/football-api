# football-api

ESPN calendars and live scores for Serie A, Serie B and UEFA Champions League.

- Run `python main.py` to refresh yesterday and the next seven calendar days in the 2026-2027 seasonal archive. Existing fixture IDs are preserved during migration.
- Run `python live.py` to refresh `data/<league>/live-current.json` and `live-yesterday.json`.
- Calendar workflow runs every 12 hours. Live workflow runs every five minutes. GitHub scheduling can be delayed.
- Both workflows share one concurrency group to serialize commits. Actions requires permission to write repository contents.
- The app reads all files through the GitHub Contents API with its existing token. Grant Contents read permission on this repository.
- The seasonal archive retains matches outside the weekly refresh window. Those dates are refreshed when they enter the window.
- Python 3.12 on Ubuntu requires no third-party packages. Windows may require `tzdata` for Europe/Rome.

Upload the complete folder contents, including .github/workflows, to the root of football-api. Run both workflows manually once after upload. The EPG remains in its existing repository.
