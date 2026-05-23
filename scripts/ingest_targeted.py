#!/usr/bin/env python3
"""
scripts/ingest_targeted.py

Targeted single state/game/date-range ingest.

Example:
  python scripts/ingest_targeted.py --state GA --game pick3 --start 2026-05-15 --end 2026-05-16

Default source is blank/all sources. Use --source lottery.net only when intentionally pinning.
Exits 1 when raw_results == 0 or observations_written == 0 unless --allow-zero is passed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from db.connection import initialize_db
from orchestrator.runner import run_ingest


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run targeted ingest for one state/game/date range.")
    p.add_argument("--state", required=True, help="State code, e.g. GA")
    p.add_argument("--game", required=True, help="Game type, e.g. pick3 or pick4")
    p.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    p.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    p.add_argument("--source", default="", help="Optional source name. Blank = all sources.")
    p.add_argument("--no-reconcile", action="store_true", help="Skip reconciliation after ingest.")
    p.add_argument("--allow-zero", action="store_true", help="Allow zero-row result without failing.")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    start_date = dt.date.fromisoformat(args.start)
    end_date = dt.date.fromisoformat(args.end)
    source = args.source.strip() or None

    initialize_db()

    summary = run_ingest(
        start_date=start_date,
        end_date=end_date,
        state=args.state.upper(),
        game_type=args.game.lower(),
        source_name=source,
        reconcile=not args.no_reconcile,
    )

    print(json.dumps(summary, indent=2, default=str))

    raw_results = int(summary.get("raw_results", 0) or 0)
    observations_written = int(summary.get("observations_written", 0) or 0)

    if not args.allow_zero:
        if raw_results == 0:
            print("ERROR: raw_results == 0 — no data fetched.", file=sys.stderr)
            return 1
        if observations_written == 0:
            print("ERROR: observations_written == 0 — no observations written.", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
