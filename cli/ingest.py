#!/usr/bin/env python3
"""
lottery_engine/cli/ingest.py

Run ingest jobs from the command line.

Examples:
    # Georgia full backfill from lottery.net, last 15 years
    python -m cli.ingest --state GA --start 2009-01-01 --end 2024-12-31

    # Georgia Pick 3 only, single source
    python -m cli.ingest --state GA --game pick3 --start 2024-01-01 --end 2024-06-30 --source lottery.net

    # All states, recent 30 days
    python -m cli.ingest --start 2024-11-01 --end 2024-11-30

    # Dry run (shows tasks without fetching)
    python -m cli.ingest --state GA --start 2024-01-01 --end 2024-01-31 --dry-run

    # Skip reconciliation (write observations only)
    python -m cli.ingest --state GA --start 2024-01-01 --end 2024-01-31 --no-reconcile
"""
import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import initialize_db
from orchestrator.runner import run_ingest


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest lottery results into the historical engine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--state",      help="State code, e.g. GA (omit for all states)")
    parser.add_argument("--game",       dest="game_type", help="Game type: pick3 | pick4")
    parser.add_argument("--source",     dest="source_name",
                        help="Source name: lottery.net | lotterycorner.com | lotteryusa.com")
    parser.add_argument("--start",      required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end",        required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Print tasks without fetching")
    parser.add_argument("--no-reconcile", action="store_true",
                        help="Write observations but skip reconciliation pass")
    parser.add_argument("--log-level",  default="INFO",
                        choices=["DEBUG","INFO","WARNING","ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    start_date = parse_date(args.start)
    end_date   = parse_date(args.end)

    if start_date > end_date:
        print(f"ERROR: --start {args.start} is after --end {args.end}", file=sys.stderr)
        sys.exit(1)

    print("Initializing database...")
    initialize_db()

    print(f"\nIngest: state={args.state or 'ALL'} game={args.game_type or 'ALL'} "
          f"source={args.source_name or 'ALL'} {start_date}..{end_date}")
    if args.dry_run:
        print("** DRY RUN — no data will be written **\n")

    summary = run_ingest(
        start_date=start_date,
        end_date=end_date,
        state=args.state,
        game_type=args.game_type,
        source_name=args.source_name,
        reconcile=not args.no_reconcile,
        dry_run=args.dry_run,
    )

    print("\n--- Ingest Summary ---")
    print(f"  Tasks run:            {summary['tasks_run']}")
    print(f"  Raw results fetched:  {summary['raw_results']}")
    print(f"  Observations written: {summary['observations_written']}")
    if summary.get("reconcile_stats"):
        rs = summary["reconcile_stats"]
        print(f"  Reconcile — accepted:         {rs.get('accepted',0)}")
        print(f"  Reconcile — duplicate:        {rs.get('duplicate',0)}")
        print(f"  Reconcile — conflict (new):   {rs.get('conflict_new_wins',0)}")
        print(f"  Reconcile — conflict (kept):  {rs.get('conflict_existing_wins',0)}")
        print(f"  Reconcile — errors:           {rs.get('errors',0)}")
    print()


if __name__ == "__main__":
    main()
