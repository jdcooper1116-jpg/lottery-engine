#!/usr/bin/env python3
"""
lottery_engine/cli/query.py

Run queries and backtests from the command line.

Examples:
    # Latest 7 results for GA pick3
    python -m cli.query latest --state GA --game pick3

    # Date range query
    python -m cli.query range --state GA --game pick3 --start 2024-01-01 --end 2024-01-31

    # Window search around a date
    python -m cli.query window --state GA --game pick3 --anchor 2024-03-15 --lookahead 7

    # Backtest candidate numbers
    python -m cli.query backtest --state GA --game pick3 --anchor 2024-03-15 --lookahead 7 --numbers 123 456 789

    # Box match backtest
    python -m cli.query backtest --state GA --game pick3 --anchor 2024-03-15 --lookahead 10 --numbers 123 --mode box
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from query.service import (
    get_draws_for_date_range, search_results_by_window,
    backtest_numbers, get_latest_results,
)
from query.models import (
    QueryFilters, DateRangeRequest, WindowSearchRequest, DreamBacktestRequest,
)


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def add_filter_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--draw-times", nargs="+", help="Restrict to draw times: morning day midday evening night")
    p.add_argument("--mode",       default="exact", help="Match mode: exact box digit pair triple presence")
    p.add_argument("--verified-only", action="store_true")
    p.add_argument("--no-conflicts",  action="store_true")
    p.add_argument("--source",     help="Filter by source name")


def build_filters(args) -> QueryFilters:
    return QueryFilters(
        draw_times=args.draw_times if hasattr(args, "draw_times") else None,
        match_mode=getattr(args, "mode", "exact"),
        include_verified_only=getattr(args, "verified_only", False),
        exclude_conflicts=getattr(args, "no_conflicts", False),
        source_name=getattr(args, "source", None),
    )


def cmd_latest(args) -> None:
    draws = get_latest_results(args.state.upper(), args.game.lower(), n=args.n)
    print(f"\n{args.state.upper()} {args.game} — last {args.n} draws")
    print(f"{'DATE':<12} {'TIME':<10} {'NUMBER':<8} {'VERIFIED'}")
    print("-" * 40)
    for d in draws:
        print(f"{d.draw_date:<12} {d.draw_time:<10} {d.winning_number:<8} {'✓' if d.is_verified else '-'}")


def cmd_range(args) -> None:
    req = DateRangeRequest(
        state=args.state.upper(), game_type=args.game.lower(),
        start_date=parse_date(args.start), end_date=parse_date(args.end),
        filters=build_filters(args),
    )
    resp = get_draws_for_date_range(req)
    print(f"\n{args.state.upper()} {args.game} — {args.start} to {args.end}: {resp.total_count} draws")
    _print_draws(resp.draws)
    if resp.coverage_gaps:
        print(f"\n  ⚠  {len(resp.coverage_gaps)} coverage gap(s) in this range")


def cmd_window(args) -> None:
    req = WindowSearchRequest(
        state=args.state.upper(), game_type=args.game.lower(),
        anchor_date=parse_date(args.anchor),
        lookahead_days=args.lookahead,
        lookbehind_days=getattr(args, "lookbehind", 0),
        filters=build_filters(args),
    )
    resp = search_results_by_window(req)
    print(f"\n{args.state.upper()} {args.game} — window {resp.window_start} to {resp.window_end}: {resp.total_count} draws")
    _print_draws(resp.draws)
    if resp.coverage_gaps:
        print(f"\n  ⚠  {len(resp.coverage_gaps)} coverage gap(s) in this window")


def cmd_backtest(args) -> None:
    req = DreamBacktestRequest(
        state=args.state.upper(), game_type=args.game.lower(),
        anchor_date=parse_date(args.anchor),
        lookahead_days=args.lookahead,
        candidates=args.numbers,
        filters=build_filters(args),
    )
    resp = backtest_numbers(req)
    print(f"\n{resp.summary}")
    if resp.hits:
        print(f"\n{'CANDIDATE':<12} {'DATE':<12} {'TIME':<10} {'WINNING':<8} {'VERIFIED'}")
        print("-" * 50)
        for h in resp.hits:
            print(f"{h.candidate:<12} {h.draw_date:<12} {h.draw_time:<10} {h.winning_number:<8} {'✓' if h.is_verified else '-'}")
    if resp.coverage_gaps:
        print(f"\n  ⚠  {len(resp.coverage_gaps)} coverage gap(s) in this window")


def _print_draws(draws) -> None:
    if not draws:
        print("  (no draws found)")
        return
    print(f"\n{'DATE':<12} {'TIME':<10} {'NUMBER':<8} {'VERIFIED'}")
    print("-" * 40)
    for d in draws:
        print(f"{d.draw_date:<12} {d.draw_time:<10} {d.winning_number:<8} {'✓' if d.is_verified else '-'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the lottery results engine")
    sub = parser.add_subparsers(dest="command", required=True)

    # latest
    p_latest = sub.add_parser("latest", help="Get most recent results")
    p_latest.add_argument("--state", required=True)
    p_latest.add_argument("--game",  required=True)
    p_latest.add_argument("--n",     type=int, default=7)

    # range
    p_range = sub.add_parser("range", help="Query a date range")
    p_range.add_argument("--state", required=True)
    p_range.add_argument("--game",  required=True)
    p_range.add_argument("--start", required=True)
    p_range.add_argument("--end",   required=True)
    add_filter_args(p_range)

    # window
    p_window = sub.add_parser("window", help="Search a window around a date")
    p_window.add_argument("--state",     required=True)
    p_window.add_argument("--game",      required=True)
    p_window.add_argument("--anchor",    required=True)
    p_window.add_argument("--lookahead", type=int, default=7)
    p_window.add_argument("--lookbehind",type=int, default=0)
    add_filter_args(p_window)

    # backtest
    p_bt = sub.add_parser("backtest", help="Backtest candidate numbers in a window")
    p_bt.add_argument("--state",     required=True)
    p_bt.add_argument("--game",      required=True)
    p_bt.add_argument("--anchor",    required=True)
    p_bt.add_argument("--lookahead", type=int, default=7)
    p_bt.add_argument("--numbers",   nargs="+", required=True, help="Candidate numbers to test")
    add_filter_args(p_bt)

    args = parser.parse_args()
    {
        "latest":   cmd_latest,
        "range":    cmd_range,
        "window":   cmd_window,
        "backtest": cmd_backtest,
    }[args.command](args)


if __name__ == "__main__":
    main()
