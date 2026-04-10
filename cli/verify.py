#!/usr/bin/env python3
"""
lottery_engine/cli/verify.py

Re-run reconciliation and report conflicts, unverified draws, and anomalies.

Examples:
    python -m cli.verify --state GA
    python -m cli.verify --state GA --show-conflicts
    python -m cli.verify --state GA --show-unverified
    python -m cli.verify --state GA --reconcile-only
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_connection
from orchestrator.reconciler import reconcile_pending


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and reconcile draw observations")
    parser.add_argument("--state",           help="Filter to state (e.g. GA)")
    parser.add_argument("--show-conflicts",  action="store_true")
    parser.add_argument("--show-unverified", action="store_true")
    parser.add_argument("--reconcile-only",  action="store_true",
                        help="Just run reconciliation, no reporting")
    args = parser.parse_args()

    print("Running reconciliation...")
    with get_connection() as conn:
        stats = reconcile_pending(conn, state=args.state)

    print(f"\nReconciliation results:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if args.reconcile_only:
        return

    with get_connection() as conn:
        if args.show_conflicts:
            _show_conflicts(conn, args.state)

        if args.show_unverified:
            _show_unverified(conn, args.state)

        _show_summary(conn, args.state)


def _show_conflicts(conn, state):
    where = "WHERE d.has_conflict=1"
    params = []
    if state:
        where += " AND d.state=?"
        params.append(state.upper())

    rows = conn.execute(
        f"""
        SELECT d.state, d.game_type, d.draw_date, d.draw_time,
               d.winning_number AS accepted, d.accepted_from_source,
               o.source_name AS conflict_src, o.winning_number AS conflict_num,
               o.conflict_note
        FROM draws d
        JOIN draw_observations o ON d.canonical_key = o.canonical_key
          AND o.reconciliation_status = 'conflict'
        {where}
        ORDER BY d.draw_date DESC
        LIMIT 50
        """,
        params,
    ).fetchall()

    print(f"\n--- Conflicts ({len(rows)} shown) ---")
    for r in rows:
        print(f"  {r['state']} {r['game_type']} {r['draw_date']} {r['draw_time']}: "
              f"accepted={r['accepted']} ({r['accepted_from_source']}) | "
              f"conflict={r['conflict_num']} ({r['conflict_src']})")


def _show_unverified(conn, state):
    where = "WHERE is_verified=0 AND has_conflict=0"
    params = []
    if state:
        where += " AND state=?"
        params.append(state.upper())

    count = conn.execute(
        f"SELECT COUNT(*) FROM draws {where}", params
    ).fetchone()[0]
    print(f"\n--- Unverified draws: {count} ---")
    print("  (Single-source only; run a secondary source to verify these.)")


def _show_summary(conn, state):
    where = ""
    params = []
    if state:
        where = "WHERE state=?"
        params.append(state.upper())

    row = conn.execute(
        f"""
        SELECT
            COUNT(*) as total,
            SUM(is_verified) as verified,
            SUM(has_conflict) as conflicts
        FROM draws {where}
        """,
        params,
    ).fetchone()

    print(f"\n--- Draws summary (state={state or 'ALL'}) ---")
    print(f"  Total canonical draws:  {row['total']}")
    print(f"  Verified (2+ sources):  {row['verified']}")
    print(f"  Has conflict flag:      {row['conflicts']}")


if __name__ == "__main__":
    main()
