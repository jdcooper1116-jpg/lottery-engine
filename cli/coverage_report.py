#!/usr/bin/env python3
"""
lottery_engine/cli/coverage_report.py

Print coverage statistics and gaps for a state.

Examples:
    python -m cli.coverage_report --state GA
    python -m cli.coverage_report --state GA --game pick3
    python -m cli.coverage_report --state GA --show-gaps
    python -m cli.coverage_report --state GA --start 2020-01-01 --end 2020-12-31 --show-gaps
"""
import argparse
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_connection
from orchestrator.coverage import get_coverage_stats


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Show scrape coverage statistics")
    parser.add_argument("--state",      required=True, help="State code, e.g. GA")
    parser.add_argument("--game",       dest="game_type", help="pick3 | pick4")
    parser.add_argument("--show-gaps",  action="store_true",
                        help="List individual not_scraped / error slots")
    parser.add_argument("--start",      help="Filter gap report start YYYY-MM-DD")
    parser.add_argument("--end",        help="Filter gap report end YYYY-MM-DD")
    parser.add_argument("--limit",      type=int, default=100,
                        help="Max gap rows to print (default 100)")
    args = parser.parse_args()

    state = args.state.upper()

    with get_connection() as conn:
        stats = get_coverage_stats(conn, state, args.game_type)

    if not stats:
        print(f"No coverage data found for state={state}")
        return

    print(f"\n{'STATE':<6} {'GAME':<8} {'TIME':<10} {'STATUS':<20} {'COUNT':>7}  {'EARLIEST':<12}  {'LATEST'}")
    print("-" * 85)
    for row in stats:
        print(
            f"{row['state']:<6} {row['game_type']:<8} {row['draw_time']:<10} "
            f"{row['coverage_status']:<20} {row['cnt']:>7}  "
            f"{row['earliest']:<12}  {row['latest']}"
        )

    if args.show_gaps:
        with get_connection() as conn:
            _print_gaps(conn, state, args.game_type, args.start, args.end, args.limit)


def _print_gaps(conn, state, game_type, start, end, limit):
    sql = """
        SELECT state, game_type, draw_date, draw_time, coverage_status,
               last_attempted_at, notes
        FROM scrape_coverage
        WHERE state=?
          AND coverage_status IN ('not_scraped','scrape_error')
    """
    params: list = [state]
    if game_type:
        sql += " AND game_type=?"
        params.append(game_type)
    if start:
        sql += " AND draw_date >= ?"
        params.append(start)
    if end:
        sql += " AND draw_date <= ?"
        params.append(end)
    sql += " ORDER BY draw_date, game_type, draw_time LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    print(f"\n--- Coverage gaps ({len(rows)} shown, limit={limit}) ---")
    if not rows:
        print("  No gaps found in this range.")
        return
    for r in rows:
        attempted = r["last_attempted_at"] or "never"
        print(f"  {r['draw_date']} {r['game_type']:8} {r['draw_time']:10} "
              f"{r['coverage_status']:18} last={attempted[:19]}")


if __name__ == "__main__":
    main()
