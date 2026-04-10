"""
lottery_engine/orchestrator/reconciler.py

Reconciles draw_observations (status='pending') into the draws table.

Rules (in priority order):
  1. New canonical_key, no existing draw:
       -> Insert draw, mark observation 'accepted'
       -> Set coverage_status = 'accepted'

  2. Existing draw, same winning_number:
       -> Mark observation 'duplicate'
       -> Increment observation_count
       -> Set is_verified=1 if observation_count >= 2

  3. Existing draw, DIFFERENT winning_number, NEW observation has HIGHER priority:
       -> Update draws.winning_number, accepted_from_source, accepted_source_priority
       -> Re-mark old accepted observation as 'conflict' with note
       -> Mark new observation 'accepted'
       -> Set has_conflict=1, coverage_status='conflict'

  4. Existing draw, DIFFERENT winning_number, NEW observation has LOWER/EQUAL priority:
       -> Mark new observation 'conflict'
       -> Set draws.has_conflict=1, coverage_status='conflict'

Run after every fetch batch. Safe to run multiple times (idempotent on
already-resolved observations).
"""
import logging
import sqlite3
from datetime import datetime, timezone

from db.connection import get_connection
from orchestrator.coverage import update_coverage
from registry.enums import CoverageStatus, ReconciliationStatus

logger = logging.getLogger(__name__)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def reconcile_pending(
    conn: sqlite3.Connection,
    state: str | None = None,
    batch_size: int = 1000,
) -> dict:
    """
    Process all pending observations. Returns summary counts.
    Processes in batches to avoid large memory use.
    """
    stats = {
        "accepted": 0,
        "duplicate": 0,
        "conflict_new_wins": 0,
        "conflict_existing_wins": 0,
        "errors": 0,
    }

    where = "WHERE o.reconciliation_status = 'pending'"
    params: list = []
    if state:
        where += " AND o.state = ?"
        params.append(state.upper())

    while True:
        pending = conn.execute(
            f"""
            SELECT o.id, o.canonical_key, o.state, o.game_type,
                   o.draw_date, o.draw_time, o.winning_number,
                   o.digit_count, o.sorted_digits,
                   o.source_name, o.source_priority, o.source_url,
                   o.scraped_at
            FROM draw_observations o
            {where}
            ORDER BY o.id
            LIMIT {batch_size}
            """,
            params,
        ).fetchall()

        if not pending:
            break

        for obs in pending:
            try:
                _reconcile_one(conn, obs, stats)
            except Exception as e:
                logger.error("Reconcile error for obs %d: %s", obs["id"], e)
                stats["errors"] += 1
                conn.execute(
                    "UPDATE draw_observations SET reconciliation_status='anomaly' WHERE id=?",
                    (obs["id"],),
                )

    logger.info("Reconciliation complete: %s", stats)
    return stats


def _reconcile_one(
    conn: sqlite3.Connection,
    obs: sqlite3.Row,
    stats: dict,
) -> None:
    obs_id     = obs["id"]
    ckey       = obs["canonical_key"]
    obs_number = obs["winning_number"]
    obs_prio   = obs["source_priority"]
    now        = now_utc()

    existing = conn.execute(
        "SELECT id, winning_number, accepted_source_priority, observation_count "
        "FROM draws WHERE canonical_key=?",
        (ckey,),
    ).fetchone()

    if existing is None:
        # Rule 1: New draw
        conn.execute(
            """
            INSERT INTO draws (
                canonical_key, state, game_type, draw_date, draw_time,
                winning_number, digit_count, sorted_digits,
                accepted_from_source, accepted_source_priority,
                observation_count, is_verified, has_conflict, accepted_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,1,0,0,?)
            """,
            (
                ckey,
                obs["state"], obs["game_type"], obs["draw_date"], obs["draw_time"],
                obs_number, obs["digit_count"], obs["sorted_digits"],
                obs["source_name"], obs_prio,
                now,
            ),
        )
        _mark_obs(conn, obs_id, ReconciliationStatus.ACCEPTED)
        update_coverage(
            conn,
            state=obs["state"], game_type=obs["game_type"],
            draw_date=obs["draw_date"], draw_time=obs["draw_time"],
            status=CoverageStatus.ACCEPTED,
            source_name=obs["source_name"],
            observation_count=1, verified_count=0,
        )
        stats["accepted"] += 1

    elif existing["winning_number"] == obs_number:
        # Rule 2: Duplicate (agreement)
        new_count = existing["observation_count"] + 1
        is_verified = 1 if new_count >= 2 else 0
        conn.execute(
            """
            UPDATE draws
            SET observation_count=?, is_verified=?
            WHERE canonical_key=?
            """,
            (new_count, is_verified, ckey),
        )
        _mark_obs(conn, obs_id, ReconciliationStatus.DUPLICATE)
        # Update coverage verified_count
        conn.execute(
            """
            UPDATE scrape_coverage
            SET verified_count = ?,
                last_attempted_at = ?,
                last_source = ?
            WHERE state=? AND game_type=? AND draw_date=? AND draw_time=?
            """,
            (
                new_count,
                now,
                obs["source_name"],
                obs["state"], obs["game_type"], obs["draw_date"], obs["draw_time"],
            ),
        )
        stats["duplicate"] += 1

    else:
        # Numbers disagree — rules 3 and 4
        existing_prio = existing["accepted_source_priority"]

        if obs_prio < existing_prio:
            # Rule 3: New observation has higher authority (lower number = higher priority)
            # Find old accepted observation and mark it as conflict
            conn.execute(
                """
                UPDATE draw_observations
                SET reconciliation_status='conflict',
                    conflict_note=?
                WHERE canonical_key=? AND reconciliation_status='accepted'
                """,
                (
                    f"Superseded by {obs['source_name']} (priority {obs_prio}). "
                    f"Old number: {existing['winning_number']}",
                    ckey,
                ),
            )
            # Update the canonical draw
            conn.execute(
                """
                UPDATE draws
                SET winning_number=?,
                    digit_count=?,
                    sorted_digits=?,
                    accepted_from_source=?,
                    accepted_source_priority=?,
                    has_conflict=1,
                    observation_count = observation_count + 1
                WHERE canonical_key=?
                """,
                (
                    obs_number,
                    obs["digit_count"],
                    obs["sorted_digits"],
                    obs["source_name"],
                    obs_prio,
                    ckey,
                ),
            )
            _mark_obs(conn, obs_id, ReconciliationStatus.ACCEPTED)
            update_coverage(
                conn,
                state=obs["state"], game_type=obs["game_type"],
                draw_date=obs["draw_date"], draw_time=obs["draw_time"],
                status=CoverageStatus.CONFLICT,
                source_name=obs["source_name"],
                observation_count=existing["observation_count"] + 1,
                notes=f"Conflict: {obs['source_name']} says {obs_number}, "
                      f"prior accepted was {existing['winning_number']}",
            )
            stats["conflict_new_wins"] += 1

        else:
            # Rule 4: Existing has higher/equal authority — reject new observation
            note = (
                f"Conflict with accepted value {existing['winning_number']} "
                f"from priority {existing_prio}. "
                f"This source (priority {obs_prio}) says {obs_number}."
            )
            _mark_obs(conn, obs_id, ReconciliationStatus.CONFLICT, note)
            conn.execute(
                "UPDATE draws SET has_conflict=1 WHERE canonical_key=?",
                (ckey,),
            )
            update_coverage(
                conn,
                state=obs["state"], game_type=obs["game_type"],
                draw_date=obs["draw_date"], draw_time=obs["draw_time"],
                status=CoverageStatus.CONFLICT,
                source_name=obs["source_name"],
                observation_count=existing["observation_count"] + 1,
                notes=note,
            )
            stats["conflict_existing_wins"] += 1


def _mark_obs(
    conn: sqlite3.Connection,
    obs_id: int,
    status: str,
    conflict_note: str | None = None,
) -> None:
    conn.execute(
        "UPDATE draw_observations SET reconciliation_status=?, conflict_note=? WHERE id=?",
        (status, conflict_note, obs_id),
    )
