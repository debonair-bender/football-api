
import argparse
import subprocess
import sys
from pathlib import Path

SCRAPERS = {
    "serie-a": "scrapers/serie_a.py",
    "serie-b": "scrapers/serie_b.py",
    "champions-league": "scrapers/champions_league.py",
}


def main():
    parser = argparse.ArgumentParser(
        description="Aggiornamento calendario"
    )

    parser.add_argument(
        "--competition",
        choices=["all", *SCRAPERS.keys()],
        default="all",
        help="Competizione da aggiornare"
    )

    args = parser.parse_args()

    selected = (
        SCRAPERS
        if args.competition == "all"
        else {args.competition: SCRAPERS[args.competition]}
    )

    errors = []

    for name, script in selected.items():
        print(f"\n=== Aggiornamento {name} ===", flush=True)

        result = subprocess.run(
            [sys.executable, script],
            check=False
        )

        if result.returncode != 0:
            errors.append(name)
            print(f"ERRORE: {name}", flush=True)
        else:
            print(f"OK: {name}", flush=True)

    if errors:
        print(
            f"\nScraper falliti: {', '.join(errors)}",
            file=sys.stderr
        )
        sys.exit(1)

    print("\nTutti gli scraper completati!")


if __name__ == "__main__":
    main()
