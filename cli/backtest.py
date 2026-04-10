#!/usr/bin/env python3
"""
lottery_engine/cli/backtest.py
Dedicated dream-number backtesting command.
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_db_path
from query.service import backtest_numbers
from query.models import DreamBacktestRequest, QueryFilters, DreamBacktestResponse

_BOLD = "\033[1m"
_GREEN = "\033[32m"
_AMBER = "\033[33m"
_RESET = "\033[0m"

def _b(s: str) -> str: return f"{_BOLD}{s}{_RESET}"
def _g(s: str) -> str: return f"{_GREEN}{s}{_RESET}"
def _a(s: str) -> str: return f"{_AMBER}{s}{_RESET}"

def _no_color() -> bool:
    import os
    return not sys.stdout.isatty() or "NO_COLOR" in os.environ

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m cli.backtest",
        description="Backtest candidate numbers against a lottery draw window.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--state", required=True, help="State code, e.g. GA")
    p.add_argument("--game", required=True, dest="game_type", help="Game type: pick3 | pick4")
    p.add_argument("--anchor", required=True, help="Anchor (dream) date YYYY-MM-DD")
    p.add_argument("--lookahead", type=int, default=7, help="Days to search after anchor (default 7, max 30)")
    p.add_argument("--candidates", required=True, help="Comma-separated candidate numbers, e.g. 297,716,999")
    p.add_argument("--label", default="", help="Optional label for this dream record")
    p.add_argument("--mode", default="exact", choices=["exact", "box", "digit", "pair", "triple", "presence"])
    p.add_argument("--draw-times", dest="draw_times", help="Restrict to draw time(s), comma-separated")
    p.add_argument("--verified-only", action="store_true", help="Only include draws confirmed by 2+ sources")
    p.add_argument("--no-conflicts", action="store_true", dest="no_conflicts", help="Exclude draws that have a source conflict flag")
    p.add_argument("--show-draws", action="store_true", help="Print all draws in the window, not just hits")
    p.add_argument("--output", default="table", choices=["table", "json"], help="Output format")
    return p

def parse_candidates(raw: str) -> list[str]:
    parts = [c.strip() for c in raw.replace(" ", ",").split(",") if c.strip()]
    bad = [c for c in parts if not c.isdigit()]
    if bad:
        raise ValueError(f"Non-digit candidates: {bad!r}")
    return parts

def parse_anchor(raw: str) -> date:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date {raw!r} — expected YYYY-MM-DD")

def print_table(resp: DreamBacktestResponse, show_draws: bool, color: bool) -> None:
    b = _b if color else lambda s: s
    g = _g if color else lambda s: s
    a = _a if color else lambda s: s

    req = resp.request
    window_str = f"{resp.window_start} → {resp.window_end}"
    cands_str = ", ".join(req.candidates)
    game_label = f"{req.state} {req.game_type.upper()}"

    print()
    print(b(f"{'─'*62}"))
    print(b(f" {game_label} Backtest"))
    if req.label:
        print(f" Label: {req.label}")
    print(f" Anchor: {req.anchor_date} | Window: {window_str} ({req.lookahead_days} days)")
    print(f" Candidates: {cands_str}")
    print(f" Match mode: {req.filters.match_mode}")
    print(b(f"{'─'*62}"))
    print()

    if resp.hits:
        print(b(g(f"HITS ({resp.hit_count})")) if color else f"HITS ({resp.hit_count})")
        print(f" {'CANDIDATE':<12} {'DATE':<12} {'TIME':<10} {'WINNING':<8} {'V':<2} SOURCE")
        print(f" {'─'*11} {'─'*11} {'─'*9} {'─'*7} {'─'} {'─'*20}")
        for h in resp.hits:
            v = "✓" if h.is_verified else " "
            src = h.source_name or "—"
            row = f" {h.candidate:<12} {h.draw_date:<12} {h.draw_time:<10} {h.winning_number:<8} {v:<2} {src}"
            print(g(row) if color else row)
        print()
        print(f" Hit dates: {', '.join(resp.hit_dates)}")
        print(f" Draw times: {', '.join(dict.fromkeys(resp.hit_draw_times))}")
    else:
        msg = "NO HITS in this window"
        print(a(msg) if color else msg)
        print()

    print(b("SUMMARY"))
    print(f" {resp.summary}")
    print()

    if show_draws and resp.all_draws:
        print(b(f"ALL DRAWS IN WINDOW ({len(resp.all_draws)})"))
        print(f" {'DATE':<12} {'TIME':<10} {'NUMBER':<8} {'V':<2} SOURCE")
        print(f" {'─'*11} {'─'*9} {'─'*7} {'─'} {'─'*20}")
        hit_keys = {h.canonical_key for h in resp.hits}
        for d in resp.all_draws:
            v = "✓" if d.is_verified else " "
            src = d.source_name or "—"
            row = f" {d.draw_date:<12} {d.draw_time:<10} {d.winning_number:<8} {v:<2} {src}"
            print(g(row) if (color and d.canonical_key in hit_keys) else row)
        print()

    if resp.coverage_gaps:
        print(a(f"⚠ COVERAGE GAPS ({len(resp.coverage_gaps)})") if color else f"WARNING: COVERAGE GAPS ({len(resp.coverage_gaps)})")
        for gap in resp.coverage_gaps:
            print(f" {gap.draw_date} {gap.draw_time:<10} {gap.coverage_status}")
        print()
        print(" Gaps mean data may not have been fetched for those slots.")

def print_json(resp: DreamBacktestResponse) -> None:
    req = resp.request
    out = {
        "state": req.state,
        "game_type": req.game_type,
        "label": req.label,
        "anchor_date": req.anchor_date.isoformat(),
        "window_start": resp.window_start.isoformat(),
        "window_end": resp.window_end.isoformat(),
        "lookahead_days": req.lookahead_days,
        "candidates": req.candidates,
        "match_mode": req.filters.match_mode,
        "hit_count": resp.hit_count,
        "hit_dates": resp.hit_dates,
        "hit_draw_times": resp.hit_draw_times,
        "summary": resp.summary,
        "hits": [
            {
                "candidate": h.candidate,
                "draw_date": h.draw_date,
                "draw_time": h.draw_time,
                "winning_number": h.winning_number,
                "match_type": h.match_type,
                "is_verified": h.is_verified,
                "source_name": h.source_name,
                "canonical_key": h.canonical_key,
            }
            for h in resp.hits
        ],
        "all_draws": [
            {
                "draw_date": d.draw_date,
                "draw_time": d.draw_time,
                "winning_number": d.winning_number,
                "is_verified": d.is_verified,
                "source_name": d.source_name,
                "canonical_key": d.canonical_key,
            }
            for d in resp.all_draws
        ],
        "coverage_gaps": [
            {
                "draw_date": g.draw_date,
                "draw_time": g.draw_time,
                "coverage_status": g.coverage_status,
                "last_attempted": g.last_attempted_at,
            }
            for g in resp.coverage_gaps
        ],
    }
    print(json.dumps(out, indent=2))

def run(args=None) -> DreamBacktestResponse:
    parser = build_parser()
    ns = parser.parse_args(args)

    try:
        candidates = parse_candidates(ns.candidates)
    except ValueError as e:
        parser.error(str(e))

    anchor = parse_anchor(ns.anchor)
    draw_times = None
    if ns.draw_times:
        draw_times = [t.strip() for t in ns.draw_times.split(",") if t.strip()]

    req = DreamBacktestRequest(
        state=ns.state.upper(),
        game_type=ns.game_type.lower(),
        anchor_date=anchor,
        lookahead_days=ns.lookahead,
        candidates=candidates,
        label=ns.label,
        filters=QueryFilters(
            draw_times=draw_times,
            match_mode=ns.mode,
            include_verified_only=ns.verified_only,
            exclude_conflicts=ns.no_conflicts,
        ),
    )

    resp = backtest_numbers(req)

    if ns.output == "json":
        print_json(resp)
    else:
        print_table(resp, show_draws=ns.show_draws, color=not _no_color())

    return resp

def main() -> None:
    run()

if __name__ == "__main__":
    main()
