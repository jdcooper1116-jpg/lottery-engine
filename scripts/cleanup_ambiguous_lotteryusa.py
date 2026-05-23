#!/usr/bin/env python3
"""
scripts/cleanup_ambiguous_lotteryusa.py

One-time (and idempotent) cleanup for draw_observations where the same
(state, game_type, draw_date, winning_number, source_url) appears across
2+ draw_time slots — the symptom of a daily-aggregate source (e.g.
lotteryusa.com) being mapped to multiple draw_time slots.

For each ambiguous group this script:
  1. Marks all matching observations reconciliation_status='anomaly'
  2. Deletes draws rows whose canonical_key matches an ambiguous observation
     AND whose only contributing source is the ambiguous one
  3. Updates scrape_coverage for affected (state, game_type, draw_date, draw_time)
     slots from 'accepted' → 'scrape_error'

Safe to run multiple times (idempotent).

Usage:
    python scripts/cleanup_ambiguous_lotteryusa.py
    python scripts/cleanup_ambiguous_lotteryusa.py --state GA --game pick3
    python scripts/cleanup_ambiguous_lotteryusa.py --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_connection, initialize_db
from orchestrator.coverage import update_coverage
from registry.enums import CoverageStatus

logger = logging.getLogger(__name__)


def run_cleanup(
    state: str | None = None,
    game_type: str | None = None,
    source_name: str | None = "lotteryusa.com",
    dry_run: bool = False,
) -> dict:
    """
    Find and clean ambiguous draw_time observations.

    Returns a summary dict:
        ambiguous_groups, observations_marked_anomaly,
        draws_deleted, coverage_slots_reverted
    """
    with get_connection() as conn:
        where_parts = ["1=1"]
        params: list = []

        if state:
            where_parts.append("state = ?")
            params.append(state)
        if game_type:
            where_parts.append("game_type = ?")
            params.append(game_type)
        if source_name:
            where_parts.append("source_name = ?")
            params.append(source_name)

        where = " AND ".join(where_parts)

        rows = conn.execute(
            f"""
            SELECT id, canonical_key, state, game_type, draw_date, draw_time,
                   winning_number, source_url, reconciliation_status
            FROM draw_observations
            WHERE {where}
            ORDER BY draw_date, state, game_type, draw_time
            """,
            params,
        ).fetchall()

    # Group by (state, game_type, draw_date, winning_number, source_url)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        key = (r["state"], r["game_type"], r["draw_date"], r["winning_number"], r["source_url"])
        groups[key].append(dict(r))

    # Keep only groups that span 2+ draw_times
    ambiguous_groups = {
        key: obs_list
        for key, obs_list in groups.items()
        if len({o["draw_time"] for o in obs_list}) >= 2
    }

    obs_ids_to_mark: list[int] = []
    canonical_keys_to_check: set[str] = set()
    affected_slots: list[tuple] = []  # (state, game_type, draw_date, draw_time)

    for key, obs_list in ambiguous_groups.items():
        for obs in obs_list:
            obs_ids_to_mark.append(obs["id"])
            canonical_keys_to_check.add(obs["canonical_key"])
            slot = (obs["state"], obs["game_type"], obs["draw_date"], obs["draw_time"])
            if slot not in affected_slots:
                affected_slots.append(slot)

    draws_to_delete: list[str] = []
    if canonical_keys_to_check:
        with get_connection() as conn:
            placeholders = ",".join("?" * len(canonical_keys_to_check))
            candidate_draws = conn.execute(
                f"""
                SELECT canonical_key, accepted_from_source
                FROM draws
                WHERE canonical_key IN ({placeholders})
                """,
                list(canonical_keys_to_check),
            ).fetchall()

        for d in candidate_draws:
            # Only remove draws that were accepted from the ambiguous source.
            # If a higher-priority source already wrote a clean draw for this key,
            # leave it alone.
            if source_name is None or d["accepted_from_source"] == source_name:
                draws_to_delete.append(d["canonical_key"])

    summary = {
        "ambiguous_groups": len(ambiguous_groups),
        "observations_marked_anomaly": len(obs_ids_to_mark),
        "draws_deleted": len(draws_to_delete),
        "coverage_slots_reverted": len(affected_slots),
    }

    logger.info(
        "Cleanup plan: %d ambiguous groups, %d obs → anomaly, "
        "%d draws → delete, %d coverage slots → scrape_error",
        summary["ambiguous_groups"],
        summary["observations_marked_anomaly"],
        summary["draws_deleted"],
        summary["coverage_slots_reverted"],
    )

    if dry_run:
        logger.info("DRY RUN — no changes written.")
        summary["dry_run"] = True
        return summary

    with get_connection() as conn:
        if obs_ids_to_mark:
            placeholders = ",".join("?" * len(obs_ids_to_mark))
            conn.execute(
                f"""
                UPDATE draw_observations
                SET reconciliation_status = 'anomaly',
                    conflict_note = 'ambiguous_draw_time: same number from same URL appeared across multiple draw_time slots'
                WHERE id IN ({placeholders})
                """,
                obs_ids_to_mark,
            )

        if draws_to_delete:
            placeholders = ",".join("?" * len(draws_to_delete))
            conn.execute(
                f"DELETE FROM draws WHERE canonical_key IN ({placeholders})",
                draws_to_delete,
            )

        for (st, gt, dd, dt) in affected_slots:
            update_coverage(
                conn,
                state=st, game_type=gt,
                draw_date=dd, draw_time=dt,
                status=CoverageStatus.SCRAPE_ERROR,
                source_name=source_name or "unknown",
                notes=(
                    "ambiguous_draw_time: same daily-aggregate result appeared "
                    "across multiple draw_time slots; coverage reverted"
                ),
            )

    logger.info("Cleanup complete: %s", summary)
    return summary


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--state",       default=None, help="State code, e.g. GA")
    p.add_argument("--game",        default=None, dest="game_type", help="pick3 | pick4")
    p.add_argument("--source",      default="lotteryusa.com", help="Source name to target")
    p.add_argument("--dry-run",     action="store_true", help="Show what would change, but write nothing")
    p.add_argument("--log-level",   default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    initialize_db()

    result = run_cleanup(
        state=args.state.upper() if args.state else None,
        game_type=args.game_type.lower() if args.game_type else None,
        source_name=args.source,
        dry_run=args.dry_run,
    )

    print("\n--- Ambiguous Draw-Time Cleanup Summary ---")
    print(f"  Ambiguous groups found:         {result['ambiguous_groups']}")
    print(f"  Observations marked anomaly:    {result['observations_marked_anomaly']}")
    print(f"  Draws deleted:                  {result['draws_deleted']}")
    print(f"  Coverage slots reverted:        {result['coverage_slots_reverted']}")
    if result.get("dry_run"):
        print("\n  *** DRY RUN — no changes were written ***")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
