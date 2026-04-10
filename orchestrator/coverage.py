"""
lottery_engine/orchestrator/coverage.py

Manages the scrape_coverage table.
Every scrape attempt — successful or not — must call update_coverage()
so the query layer can distinguish "no result" from "never tried".

Coverage status flow:
    not_scraped
        -> scrape_attempted, no draw scheduled  -> no_draw_scheduled
        -> scrape_attempted, result accepted     -> accepted
        -> scrape_attempted, sources conflict    -> conflict
        -> scrape_attempted, result anomaly      -> anomaly
        -> scrape_attempted, fetch failed        -> scrape_error
"""
import sqlite3
from datetime import datetime, timezone
from registry.enums import CoverageStatus
from db.connection import get_connection


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def mark_not_scraped(
    conn: sqlite3.Connection,
    state: str,
    game_type: str,
    draw_date: str,
    draw_time: str,
) -> None:
    """Insert a slot as not_scraped if it doesn't exist yet."""
    conn.execute(
        """
        INSERT OR IGNORE INTO scrape_coverage
            (state, game_type, draw_date, draw_time, coverage_status,
             observation_count, verified_count)
        VALUES (?,?,?,?,?,0,0)
        """,
        (state, game_type, draw_date, draw_time, CoverageStatus.NOT_SCRAPED),
    )


def update_coverage(
    conn: sqlite3.Connection,
    state: str,
    game_type: str,
    draw_date: str,
    draw_time: str,
    status: str,
    source_name: str,
    observation_count: int = 1,
    verified_count: int = 0,
    notes: str | None = None,
) -> None:
    """Upsert coverage status for a (state, game, date, draw_time) slot."""
    now = now_utc()
    conn.execute(
        """
        INSERT INTO scrape_coverage
            (state, game_type, draw_date, draw_time,
             coverage_status, observation_count, verified_count,
             last_attempted_at, last_source, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(state, game_type, draw_date, draw_time) DO UPDATE SET
            coverage_status    = excluded.coverage_status,
            observation_count  = excluded.observation_count,
            verified_count     = excluded.verified_count,
            last_attempted_at  = excluded.last_attempted_at,
            last_source        = excluded.last_source,
            notes              = COALESCE(excluded.notes, scrape_coverage.notes)
        """,
        (
            state, game_type, draw_date, draw_time,
            status, observation_count, verified_count,
            now, source_name, notes,
        ),
    )


def mark_scrape_error(
    conn: sqlite3.Connection,
    state: str,
    game_type: str,
    draw_date: str,
    draw_time: str,
    source_name: str,
    error_note: str,
) -> None:
    update_coverage(
        conn, state, game_type, draw_date, draw_time,
        status=CoverageStatus.SCRAPE_ERROR,
        source_name=source_name,
        notes=error_note,
    )


def mark_no_draw_scheduled(
    conn: sqlite3.Connection,
    state: str,
    game_type: str,
    draw_date: str,
    draw_time: str,
) -> None:
    """
    Mark a slot as no_draw_scheduled.
    Called by the scheduler when a job's lifecycle window excludes a date.
    """
    update_coverage(
        conn, state, game_type, draw_date, draw_time,
        status=CoverageStatus.NO_DRAW_SCHEDULED,
        source_name="scheduler",
    )


def initialize_coverage_slots(
    conn: sqlite3.Connection,
    state: str,
    game_type: str,
    draw_time: str,
    start_date: str,
    end_date: str,
) -> int:
    """
    Bulk-insert not_scraped slots for a (state, game, draw_time) over a date range.
    Uses a recursive CTE to generate dates. Returns count of new rows inserted.
    """
    result = conn.execute(
        """
        WITH RECURSIVE dates(d) AS (
            SELECT ?
            UNION ALL
            SELECT DATE(d, '+1 day') FROM dates WHERE d < ?
        )
        INSERT OR IGNORE INTO scrape_coverage
            (state, game_type, draw_date, draw_time, coverage_status,
             observation_count, verified_count)
        SELECT ?, ?, d, ?, ?, 0, 0
        FROM dates
        """,
        (start_date, end_date, state, game_type, draw_time, CoverageStatus.NOT_SCRAPED),
    )
    return result.rowcount


def get_coverage_stats(
    conn: sqlite3.Connection,
    state: str,
    game_type: str | None = None,
) -> list[dict]:
    """Return coverage counts grouped by state/game/status."""
    if game_type:
        rows = conn.execute(
            """
            SELECT state, game_type, draw_time, coverage_status, COUNT(*) as cnt,
                   MIN(draw_date) as earliest, MAX(draw_date) as latest
            FROM scrape_coverage
            WHERE state=? AND game_type=?
            GROUP BY state, game_type, draw_time, coverage_status
            ORDER BY game_type, draw_time, coverage_status
            """,
            (state, game_type),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT state, game_type, draw_time, coverage_status, COUNT(*) as cnt,
                   MIN(draw_date) as earliest, MAX(draw_date) as latest
            FROM scrape_coverage
            WHERE state=?
            GROUP BY state, game_type, draw_time, coverage_status
            ORDER BY game_type, draw_time, coverage_status
            """,
            (state,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_not_scraped_dates(
    conn: sqlite3.Connection,
    state: str,
    game_type: str,
    draw_time: str,
    limit: int = 500,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT draw_date FROM scrape_coverage
        WHERE state=? AND game_type=? AND draw_time=?
          AND coverage_status='not_scraped'
        ORDER BY draw_date
        LIMIT ?
        """,
        (state, game_type, draw_time, limit),
    ).fetchall()
    return [r["draw_date"] for r in rows]
