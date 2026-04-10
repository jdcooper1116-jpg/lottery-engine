"""
lottery_engine/orchestrator/runner.py

Main ingest loop. Ties together:
  scheduler  -> builds FetchTask list
  parsers    -> fetch raw results from sources
  db write   -> insert into draw_observations
  coverage   -> upsert scrape_coverage
  reconciler -> promote observations to canonical draws

Usage (programmatic):
    from orchestrator.runner import run_ingest
    run_ingest(state="GA", start_date=date(2024,1,1), end_date=date(2024,3,31))

Usage (CLI):
    python -m cli.ingest --state GA --start 2024-01-01 --end 2024-03-31
"""
from __future__ import annotations
import logging
from datetime import date
from typing import Optional

from db.connection import get_connection, execute_batch
from orchestrator.scheduler import build_tasks, FetchTask
from orchestrator.reconciler import reconcile_pending
from orchestrator.coverage import update_coverage
from sources import get_parser
from sources.base import RawDrawResult
from registry.enums import CoverageStatus

logger = logging.getLogger(__name__)


def run_ingest(
    start_date:  date,
    end_date:    date,
    state:       Optional[str]  = None,
    game_type:   Optional[str]  = None,
    source_name: Optional[str]  = None,
    reconcile:   bool           = True,
    dry_run:     bool           = False,
) -> dict:
    """
    Full ingest pass for a date range.

    Returns a summary dict:
      tasks_run, raw_results, observations_written, reconcile_stats
    """
    tasks = build_tasks(
        start_date=start_date,
        end_date=end_date,
        state=state,
        game_type=game_type,
        source_name=source_name,
    )

    logger.info(
        "Starting ingest: %d tasks | %s | %s..%s",
        len(tasks), state or "all states", start_date, end_date,
    )

    total_raw     = 0
    total_written = 0

    for task in tasks:
        if dry_run:
            _print_dry_run_task(task)
            total_raw += 1   # count task, not rows
            continue

        raw_results = _run_task(task)
        total_raw += len(raw_results)

        if raw_results:
            written = _write_observations(raw_results, task)
            total_written += written
        else:
            # Record that we attempted but got nothing
            _mark_empty_task(task)

    reconcile_stats: dict = {}
    if reconcile and not dry_run:
        logger.info("Running reconciliation...")
        with get_connection() as conn:
            reconcile_stats = reconcile_pending(conn, state=state)

    summary = {
        "tasks_run":            len(tasks),
        "raw_results":          total_raw,
        "observations_written": total_written,
        "reconcile_stats":      reconcile_stats,
    }
    logger.info("Ingest complete: %s", summary)
    return summary


def _run_task(task: FetchTask) -> list[RawDrawResult]:
    """Run one FetchTask through its parser."""
    parser = get_parser(task.mapping.source_name)
    if parser is None:
        logger.warning("No parser for source: %s", task.mapping.source_name)
        return []
    try:
        return parser.fetch_results(
            mapping=task.mapping,
            start_date=task.start_date,
            end_date=task.end_date,
        )
    except Exception as e:
        logger.error("Parser error for task %s: %s", task.label, e)
        return []


def _write_observations(results: list[RawDrawResult], task: FetchTask) -> int:
    """
    Bulk-insert raw results into draw_observations as 'pending'.
    Returns count written.
    Uses INSERT OR IGNORE so duplicate scrape runs don't double-insert.
    """
    rows = [
        (
            r.canonical_key,
            r.state, r.game_type, r.draw_date, r.draw_time,
            r.winning_number, r.digit_count, r.sorted_digits,
            r.source_name, r.source_priority, r.source_url,
            r.scraped_at,
            "pending",
            None,               # conflict_note
            r.raw_draw_time_label,
        )
        for r in results
    ]

    sql = """
        INSERT OR IGNORE INTO draw_observations (
            canonical_key,
            state, game_type, draw_date, draw_time,
            winning_number, digit_count, sorted_digits,
            source_name, source_priority, source_url,
            scraped_at, reconciliation_status, conflict_note,
            raw_draw_time_label
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    # Write in a single transaction per task for speed
    with get_connection() as conn:
        written = execute_batch(conn, sql, rows)

        # Mark coverage: accepted for each distinct (date, draw_time) seen
        seen: set[tuple] = set()
        for r in results:
            slot = (r.state, r.game_type, r.draw_date, r.draw_time)
            if slot not in seen:
                seen.add(slot)
                update_coverage(
                    conn,
                    state=r.state, game_type=r.game_type,
                    draw_date=r.draw_date, draw_time=r.draw_time,
                    status=CoverageStatus.ACCEPTED,
                    source_name=r.source_name,
                    observation_count=1,
                )

    logger.debug("  Wrote %d observations for task %s", written, task.label)
    return written


def _mark_empty_task(task: FetchTask) -> None:
    """
    When a fetch returns zero results, mark coverage slots as scrape_error
    so the system knows the attempt was made.
    """
    j = task.mapping.job_def
    from sources.base import date_range_months
    from datetime import date as date_type

    with get_connection() as conn:
        for year, month in date_range_months(task.start_date, task.end_date):
            # Only mark the first of each month to avoid flooding the table
            slot_date = f"{year}-{month:02d}-01"
            update_coverage(
                conn,
                state=j.state, game_type=j.game_type,
                draw_date=slot_date, draw_time=j.draw_time,
                status=CoverageStatus.SCRAPE_ERROR,
                source_name=task.mapping.source_name,
                notes="Fetch returned 0 results",
            )

def _print_dry_run_task(task: FetchTask) -> None:
    """
    Print the task details and all URLs it would generate — no HTTP requests made.
    Iterates the same (year, month) loop the real fetcher uses so URLs are exact.
    """
    from sources.base import date_range_months
    j = task.mapping.job_def
    print(f"  TASK  {j.state} | {j.game_type} | {j.draw_time} | {task.mapping.source_name}")
    print(f"        game_slug = {task.mapping.source_game_slug!r}")
    print(f"        range     = {task.start_date} .. {task.end_date}")
    seen_urls: set[str] = set()
    for year, month in date_range_months(task.start_date, task.end_date):
        if not task.mapping.covers_year(year):
            continue
        url = task.mapping.build_url(year=year, month=month)
        if url and url not in seen_urls:
            seen_urls.add(url)
            print(f"        URL       = {url}")
    print()
