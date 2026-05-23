#!/usr/bin/env python3
"""
Targeted ingest for a single state/game/date-range.

Tries all registered sources (lottery.net → lotterycorner.com → lotteryusa.com)
unless --source is specified.

Examples:
    python scripts/ingest_targeted.py --state GA --game pick3 --start 2026-05-15 --end 2026-05-16
    python scripts/ingest_targeted.py --state GA --game pick4 --start 2026-05-15 --end 2026-05-16
    python scripts/ingest_targeted.py --state GA --game pick3 --start 2026-05-15 --end 2026-05-16 --source lotterycorner.com
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import initialize_db
from orchestrator.runner import run_ingest


def parse_date(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y-%m-%d").date()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--state",   required=True, help="State code, e.g. GA")
    p.add_argument("--game",    required=True, dest="game_type", help="pick3 | pick4")
    p.add_argument("--start",   required=True, type=parse_date, help="Start date YYYY-MM-DD")
    p.add_argument("--end",     required=True, type=parse_date, help="End date YYYY-MM-DD")
    p.add_argument("--source",  default=None,  help="lottery.net | lotterycorner.com | lotteryusa.com  (omit = all)")
    p.add_argument("--no-reconcile", action="store_true", help="Skip reconciliation pass")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print("Initializing database...")
    initialize_db()

    print(
        f"\nTargeted ingest: state={args.state.upper()}  game={args.game_type}"
        f"  source={args.source or 'all'}"
        f"  {args.start}..{args.end}"
    )

    summary = run_ingest(
        start_date=args.start,
        end_date=args.end,
        state=args.state,
        game_type=args.game_type,
        source_name=args.source,
        reconcile=not args.no_reconcile,
    )

    print("\n--- Targeted Ingest Summary ---")
    print(f"  Tasks run:            {summary['tasks_run']}")
    print(f"  Raw results fetched:  {summary['raw_results']}")
    print(f"  Observations written: {summary['observations_written']}")
    if summary.get("reconcile_stats"):
        rs = summary["reconcile_stats"]
        print(f"  Reconcile — accepted:         {rs.get('accepted', 0)}")
        print(f"  Reconcile — duplicate:        {rs.get('duplicate', 0)}")
        print(f"  Reconcile — conflict (new):   {rs.get('conflict_new_wins', 0)}")
        print(f"  Reconcile — conflict (kept):  {rs.get('conflict_existing_wins', 0)}")
        print(f"  Reconcile — errors:           {rs.get('errors', 0)}")
    print()

    if summary["raw_results"] == 0:
        print("WARNING: 0 raw results returned — source pages may be unavailable.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
