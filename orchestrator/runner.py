"""
lottery_engine/orchestrator/runner.py

Main ingest loop. Ties together:
  scheduler  -> builds FetchTask list
  parsers    -> fetch raw results from sources
  db write   -> insert into draw_observations
  coverage   -> upsert scrape_coverage
  reconciler -> promote observations to canonical draws

Two-phase pipeline:
  Phase 1: fetch all tasks → collect (task, results) pairs
  Phase 2: cross-task sanity check — detect same-URL draw_time duplication
           (a daily-aggregate source spread across multiple draw_time slots)
  Phase 3: write clean results; mark ambiguous/empty tasks as scrape_error

Usage (programmatic):
    from orchestrator.runner import run_ingest
    run_ingest(state="GA", start_date=date(2024,1,1), end_date=date(2024,3,31))

Usage (CLI):
    python -m cli.ingest --state GA --start 2024-01-01 --end 2024-03-31
"""
from __future__ import annotations
import logging
from collections import defaultdict
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
      tasks_run, raw_results, observations_written, ambiguous_discarded,
      reconcile_stats
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

    total_raw          = 0
    total_written      = 0
    ambiguous_discarded = 0

    if dry_run:
        for task in tasks:
            _print_dry_run_task(task)
            total_raw += 1
    else:
        # ------------------------------------------------------------------
        # Phase 1: fetch all tasks
        # ------------------------------------------------------------------
        task_results: list[tuple[FetchTask, list[RawDrawResult]]] = []
        for task in tasks:
            raw = _run_task(task)
            task_results.append((task, raw))
            total_raw += len(raw)

        # ------------------------------------------------------------------
        # Phase 2: cross-task duplication check
        # Detect when the same (state, game_type, date, number, source_url)
        # appears across 2+ draw_times — sign that a daily-aggregate page was
        # spread across specific draw_time slots without explicit labeling.
        # ------------------------------------------------------------------
        all_results = [r for _, res in task_results for r in res]
        ambiguous_url_keys = _find_ambiguous_url_draw_time_keys(all_results)

        if ambiguous_url_keys:
            ambiguous_discarded = sum(
                1 for r in all_results
                if _url_draw_key(r) in ambiguous_url_keys
            )
            bad_sources = {k[4] for k in ambiguous_url_keys}
            logger.warning(
                "Ambiguous draw_time duplication: same winning_number from %s "
                "appears across multiple draw_time slots from the same URL. "
                "Discarding %d results.",
                bad_sources, ambiguous_discarded,
            )

        # ------------------------------------------------------------------
        # Phase 3: write clean results; mark ambiguous/empty tasks
        # ------------------------------------------------------------------
        for task, raw_results in task_results:
            clean = [
                r for r in raw_results
                if _url_draw_key(r) not in ambiguous_url_keys
            ]
            had_ambiguous = len(clean) < len(raw_results)

            if clean:
                written = _write_observations(clean, task)
                total_written += written
            else:
                notes = (
                    "ambiguous_draw_time: daily-aggregate source result duplicated "
                    "across draw_time slots from same URL"
                    if had_ambiguous
                    else "Fetch returned 0 results"
                )
                _mark_empty_task(task, notes=notes)

    reconcile_stats: dict = {}
    if reconcile and not dry_run:
        logger.info("Running reconciliation...")
        with get_connection() as conn:
            reconcile_stats = reconcile_pending(conn, state=state)

    summary = {
        "tasks_run":             len(tasks),
        "raw_results":           total_raw,
        "observations_written":  total_written,
        "ambiguous_discarded":   ambiguous_discarded,
        "reconcile_stats":       reconcile_stats,
    }
    logger.info("Ingest complete: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# Ambiguous draw_time detection
# ---------------------------------------------------------------------------

def _url_draw_key(r: RawDrawResult) -> tuple:
    """Key that groups results from the same source URL on the same date."""
    return (r.state, r.game_type, r.draw_date, r.winning_number, r.source_url)


def _find_ambiguous_url_draw_time_keys(
    results: list[RawDrawResult],
) -> set[tuple]:
    """
    Return the set of _url_draw_key values where the same (state, game_type,
    draw_date, winning_number, source_url) appears for 2+ distinct draw_times.

    This catches daily-aggregate sources (e.g. lotteryusa.com GA) that return
    one result per day but get fetched once per draw_time mapping, causing the
    same number to be recorded as midday, evening, AND night.
    """
    groups: dict[tuple, set[str]] = defaultdict(set)
    for r in results:
        groups[_url_draw_key(r)].add(r.draw_time)
    return {key for key, draw_times in groups.items() if len(draw_times) >= 2}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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

    with get_connection() as conn:
        written = execute_batch(conn, sql, rows)

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


def _mark_empty_task(task: FetchTask, notes: str = "Fetch returned 0 results") -> None:
    """
    Mark coverage slots as scrape_error so the system records that an attempt
    was made but produced no usable data.
    """
    j = task.mapping.job_def
    from sources.base import date_range_months

    with get_connection() as conn:
        for year, month in date_range_months(task.start_date, task.end_date):
            slot_date = f"{year}-{month:02d}-01"
            update_coverage(
                conn,
                state=j.state, game_type=j.game_type,
                draw_date=slot_date, draw_time=j.draw_time,
                status=CoverageStatus.SCRAPE_ERROR,
                source_name=task.mapping.source_name,
                notes=notes,
            )


def _print_dry_run_task(task: FetchTask) -> None:
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
