"""
lottery_engine/query/coverage_checker.py

Bridges the query service and the scrape_coverage table.

The key responsibility is distinguishing between:
  - "no draw scheduled" (job lifecycle says this slot never existed)
  - "not yet scraped"   (slot exists in schedule but we haven't fetched it)
  - "no result found"   (we fetched it and got nothing — genuine empty)

This module is the ONLY place that joins registry lifecycle data with
the scrape_coverage table to answer coverage questions.
"""
from __future__ import annotations
import sqlite3
from datetime import date, timedelta
from typing import Optional

from registry.loader import get_jobs_for_state
from query.models import CoverageGap


def get_coverage_gaps(
    conn: sqlite3.Connection,
    state: str,
    game_type: str,
    start_date: date,
    end_date:   date,
    draw_times: Optional[list[str]] = None,
) -> list[CoverageGap]:
    """
    Return slots in the date range that are not_scraped or scrape_error,
    but only for dates when a draw was actually scheduled (per registry).

    Dates that fall outside the job's active_start_date / active_end_date
    are excluded — those are never gaps, they are correct absences.
    """
    gaps: list[CoverageGap] = []

    # Get scheduled jobs for this state/game over the date range
    scheduled_slots = _build_scheduled_slots(
        state, game_type, start_date, end_date, draw_times
    )
    if not scheduled_slots:
        return gaps

    # Query coverage for the date range
    dt_filter = ""
    params: list = [state, game_type, start_date.isoformat(), end_date.isoformat()]
    if draw_times:
        placeholders = ",".join("?" * len(draw_times))
        dt_filter = f"AND draw_time IN ({placeholders})"
        params.extend(draw_times)

    rows = conn.execute(
        f"""
        SELECT draw_date, draw_time, coverage_status, last_attempted_at
        FROM scrape_coverage
        WHERE state=? AND game_type=?
          AND draw_date BETWEEN ? AND ?
          {dt_filter}
          AND coverage_status IN ('not_scraped','scrape_error')
        ORDER BY draw_date, draw_time
        """,
        params,
    ).fetchall()

    coverage_map = {
        (r["draw_date"], r["draw_time"]): r
        for r in rows
    }

    # Report gaps only for scheduled slots
    for slot_date, slot_time in scheduled_slots:
        slot_key = (slot_date.isoformat(), slot_time)
        if slot_key in coverage_map:
            row = coverage_map[slot_key]
            gaps.append(CoverageGap(
                draw_date=row["draw_date"],
                draw_time=row["draw_time"],
                coverage_status=row["coverage_status"],
                last_attempted_at=row["last_attempted_at"],
            ))
        else:
            # Slot is scheduled but has NO coverage row at all = never attempted
            gaps.append(CoverageGap(
                draw_date=slot_date.isoformat(),
                draw_time=slot_time,
                coverage_status="not_scraped",
                last_attempted_at=None,
            ))

    return gaps


def slot_is_scheduled(
    state: str,
    game_type: str,
    draw_date: date,
    draw_time: str,
) -> bool:
    """
    Returns True if the registry has an active job for this slot on draw_date.
    Used by the query service to annotate "no draw scheduled" correctly.
    """
    jobs = get_jobs_for_state(state, game_type=game_type, target_date=draw_date)
    return any(j.draw_time == draw_time for j in jobs)


def _build_scheduled_slots(
    state: str,
    game_type: str,
    start_date: date,
    end_date: date,
    draw_times: Optional[list[str]],
) -> list[tuple[date, str]]:
    """
    Build the complete list of (date, draw_time) pairs that SHOULD
    have data, based on registry job lifecycle windows.
    """
    slots: list[tuple[date, str]] = []
    current = start_date
    while current <= end_date:
        jobs = get_jobs_for_state(state, game_type=game_type, target_date=current)
        for job in jobs:
            if draw_times and job.draw_time not in draw_times:
                continue
            if _draw_is_scheduled_on_day(job, current):
                slots.append((current, job.draw_time))
        current += timedelta(days=1)
    return slots


def _draw_is_scheduled_on_day(job, target: date) -> bool:
    """Check draw_days field against target date."""
    days_field = job.draw_days.lower()
    if days_field == "daily":
        return True
    if days_field == "mon-sat":
        return target.weekday() < 6
    if days_field == "mon-fri":
        return target.weekday() < 5
    # JSON array format: ["mon","wed","fri"]
    try:
        import json
        day_list = json.loads(days_field)
        day_names = ["mon","tue","wed","thu","fri","sat","sun"]
        return day_names[target.weekday()] in [d.lower() for d in day_list]
    except Exception:
        return True  # unknown format, assume scheduled
