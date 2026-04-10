"""
lottery_engine/registry/seed.py

Writes draw_job_definitions and source_job_mappings to the database.
Safe to re-run: uses INSERT OR IGNORE for idempotency.

Usage:
    python -m registry.seed                   # seeds all states
    python -m registry.seed --state GA        # seeds only Georgia
    python -m registry.seed --verify          # prints what is in the DB
"""
import argparse
import sqlite3
import sys
from pathlib import Path

# Allow running as __main__
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_connection, initialize_db
from registry.definitions import ALL_JOB_DEFINITIONS, ALL_SOURCE_MAPPINGS
from registry.models import DrawJobDef, SourceJobMapping


def seed_job_definitions(
    conn: sqlite3.Connection,
    jobs: list[DrawJobDef],
) -> dict[str, int]:
    """
    Insert job definitions into draw_job_definitions.
    Returns a mapping of (state|game_type|draw_time|version) -> db_id.
    """
    id_map: dict[str, int] = {}
    for job in jobs:
        conn.execute(
            """
            INSERT OR IGNORE INTO draw_job_definitions (
                state, game_type, draw_time, draw_label, schedule_version,
                active_start_date, active_end_date,
                source_min_year, source_max_year,
                draw_days, canonical_time_key, notes, is_active
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                job.state,
                job.game_type,
                job.draw_time,
                job.draw_label,
                job.schedule_version,
                job.active_start_date.isoformat() if job.active_start_date else None,
                job.active_end_date.isoformat()   if job.active_end_date   else None,
                job.source_min_year,
                job.source_max_year,
                job.draw_days,
                job.canonical_time_key,
                job.notes,
                1 if job.is_active else 0,
            ),
        )
        row = conn.execute(
            """
            SELECT id FROM draw_job_definitions
            WHERE state=? AND game_type=? AND draw_time=? AND schedule_version=?
            """,
            (job.state, job.game_type, job.draw_time, job.schedule_version),
        ).fetchone()
        if row:
            key = f"{job.state}|{job.game_type}|{job.draw_time}|{job.schedule_version}"
            id_map[key] = row["id"]
            job.db_id = row["id"]
    return id_map


def seed_source_mappings(
    conn: sqlite3.Connection,
    mappings: list[SourceJobMapping],
    job_id_map: dict[str, int],
) -> int:
    """
    Insert source_job_mappings. Returns count of rows inserted.
    """
    inserted = 0
    for mapping in mappings:
        j = mapping.job_def
        key = f"{j.state}|{j.game_type}|{j.draw_time}|{j.schedule_version}"
        job_db_id = job_id_map.get(key) or j.db_id
        if job_db_id is None:
            print(f"  WARN: no DB id found for job {key}, skipping mapping for {mapping.source_name}")
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO source_job_mappings (
                job_definition_id, source_name, source_priority,
                source_state_slug, source_game_slug, source_draw_time_label,
                url_template, source_min_year, source_max_year,
                is_enabled, notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                job_db_id,
                mapping.source_name,
                mapping.source_priority,
                mapping.source_state_slug,
                mapping.source_game_slug,
                mapping.source_draw_time_label,
                mapping.url_template,
                mapping.source_min_year,
                mapping.source_max_year,
                1 if mapping.is_enabled else 0,
                mapping.notes,
            ),
        )
        inserted += 1
    return inserted


def seed_state(conn: sqlite3.Connection, state: str | None = None) -> None:
    jobs = [j for j in ALL_JOB_DEFINITIONS if state is None or j.state == state.upper()]
    maps = [m for m in ALL_SOURCE_MAPPINGS if state is None or m.job_def.state == state.upper()]

    if not jobs:
        print(f"No job definitions found for state={state!r}")
        return

    print(f"Seeding {len(jobs)} job definitions...")
    job_id_map = seed_job_definitions(conn, jobs)
    print(f"  {len(job_id_map)} job definitions in DB")

    print(f"Seeding {len(maps)} source mappings...")
    n = seed_source_mappings(conn, maps, job_id_map)
    print(f"  {n} source mappings processed")


def verify(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT state, game_type, draw_time, draw_label, schedule_version, "
        "active_start_date, source_min_year, is_active "
        "FROM draw_job_definitions ORDER BY state, game_type, draw_time"
    ).fetchall()
    print(f"\n{'STATE':<6} {'GAME':<8} {'TIME':<10} {'LABEL':<35} {'VER':<4} {'START':<12} {'MIN_YR':<8} ACTIVE")
    print("-" * 95)
    for r in rows:
        print(
            f"{r['state']:<6} {r['game_type']:<8} {r['draw_time']:<10} "
            f"{r['draw_label']:<35} {r['schedule_version']:<4} "
            f"{str(r['active_start_date'] or 'NULL'):<12} "
            f"{str(r['source_min_year'] or 'NULL'):<8} "
            f"{'YES' if r['is_active'] else 'NO'}"
        )

    mapping_count = conn.execute("SELECT COUNT(*) FROM source_job_mappings").fetchone()[0]
    print(f"\n{mapping_count} source mappings total")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed registry tables")
    parser.add_argument("--state", help="Seed only this state (e.g. GA)")
    parser.add_argument("--verify", action="store_true", help="Print current DB contents")
    args = parser.parse_args()

    print("Initializing database...")
    initialize_db()

    with get_connection() as conn:
        if args.verify:
            verify(conn)
        else:
            seed_state(conn, args.state)
            print("\nVerification:")
            verify(conn)
    print("\nDone.")


if __name__ == "__main__":
    main()
