#!/usr/bin/env python3
"""
scripts/export_observations_for_import.py

Export trusted draw_observations from the local DB as a JSON payload
compatible with POST /admin/import/observations.

Examples:
    python3 scripts/export_observations_for_import.py \\
        --state GA --game pick3 \\
        --start 2026-05-15 --end 2026-05-22 \\
        --source lottery.net \\
        --out /tmp/ga_pick3_import.json

    # Produce a write-mode body (dry_run=false):
    python3 scripts/export_observations_for_import.py \\
        --state GA --game pick3 --start 2026-05-15 --end 2026-05-22 \\
        --source lottery.net --write-body \\
        --out /tmp/ga_pick3_import_write.json
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def get_db_path() -> str:
    return os.environ.get(
        "LOTTERY_DB_PATH",
        str(Path(__file__).parent.parent / "data" / "history_all_states.db"),
    )


def open_readonly(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def export_rows(
    db_path: str,
    state: str,
    game_type: str,
    start: str,
    end: str,
    source: str,
    status_filter: list[str],
) -> list[dict]:
    conn = open_readonly(db_path)
    placeholders = ",".join("?" * len(status_filter))
    rows = conn.execute(
        f"""
        SELECT
            state, game_type, draw_date, draw_time,
            winning_number, digit_count, sorted_digits,
            source_name, source_url,
            COALESCE(raw_draw_time_label, '') AS raw_draw_time_label,
            reconciliation_status, scraped_at
        FROM draw_observations
        WHERE state      = ?
          AND game_type  = ?
          AND draw_date >= ?
          AND draw_date <= ?
          AND source_name = ?
          AND reconciliation_status IN ({placeholders})
        ORDER BY draw_date, draw_time
        """,
        [state.upper(), game_type.lower(), start, end, source, *status_filter],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--state",   required=True, help="State code, e.g. GA")
    p.add_argument("--game",    required=True, dest="game_type", help="pick3 | pick4")
    p.add_argument("--start",   required=True, help="Start date YYYY-MM-DD (inclusive)")
    p.add_argument("--end",     required=True, help="End date YYYY-MM-DD (inclusive)")
    p.add_argument("--source",  default="lottery.net",
                   help="source_name filter (default: lottery.net)")
    p.add_argument("--status",  default="accepted,duplicate",
                   help="Comma-separated reconciliation_status values to include "
                        "(default: accepted,duplicate)")
    p.add_argument("--out",     default=None,
                   help="Output JSON file path (default: stdout)")
    p.add_argument("--write-body", action="store_true",
                   help="Set dry_run=false in output body (default: dry_run=true)")
    p.add_argument("--batch-label", default=None,
                   help="Optional batch_label string for the import body")
    p.add_argument("--db-path", default=None,
                   help="SQLite DB path (default: $LOTTERY_DB_PATH)")
    p.add_argument("--reconcile", action="store_true", default=True,
                   help="Set reconcile=true in output body (default: true)")
    p.add_argument("--no-reconcile", dest="reconcile", action="store_false")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    db_path = args.db_path or get_db_path()
    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        print("Set LOTTERY_DB_PATH or pass --db-path.", file=sys.stderr)
        return 1

    status_filter = [s.strip() for s in args.status.split(",") if s.strip()]
    rows = export_rows(
        db_path=db_path,
        state=args.state,
        game_type=args.game_type,
        start=args.start,
        end=args.end,
        source=args.source,
        status_filter=status_filter,
    )

    if not rows:
        print(
            f"WARNING: No rows found for {args.state.upper()} {args.game_type} "
            f"{args.start}..{args.end} source={args.source} "
            f"status={status_filter}",
            file=sys.stderr,
        )

    # Build import-compatible row dicts (only fields the endpoint needs)
    import_rows = [
        {
            "state":              r["state"],
            "game_type":          r["game_type"],
            "draw_date":          r["draw_date"],
            "draw_time":          r["draw_time"],
            "winning_number":     r["winning_number"],
            "source_name":        r["source_name"],
            "source_url":         r["source_url"] or "",
            "raw_draw_time_label": r["raw_draw_time_label"],
        }
        for r in rows
    ]

    batch_label = args.batch_label or (
        f"{args.state.lower()}-{args.game_type}-"
        f"{args.start}-to-{args.end}-{args.source.replace('.', '-')}"
    )

    body = {
        "dry_run":     not args.write_body,
        "reconcile":   args.reconcile,
        "batch_label": batch_label,
        "source_name": args.source,
        "rows":        import_rows,
    }

    output = json.dumps(body, indent=2, ensure_ascii=False)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Wrote {len(import_rows)} row(s) to {args.out}", file=sys.stderr)
        print(f"dry_run={body['dry_run']}  reconcile={body['reconcile']}", file=sys.stderr)
    else:
        print(output)

    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
