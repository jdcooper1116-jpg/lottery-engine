"""
lottery_engine/orchestrator/scheduler.py

Builds a list of fetch tasks from the registry for a given
(state, game_type, date_range, source_name) combination.

Each task is a (SourceJobMapping, start_date, end_date) triple
that the runner passes to the appropriate parser.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional

from registry.loader import get_all_states, get_jobs_for_state, get_source_mappings_for_job
from registry.models import DrawJobDef, SourceJobMapping
from registry.enums import SourceName


@dataclass
class FetchTask:
    mapping:    SourceJobMapping
    start_date: date
    end_date:   date

    @property
    def label(self) -> str:
        j = self.mapping.job_def
        return (
            f"{j.state} | {j.game_type} | {j.draw_time} | "
            f"{self.mapping.source_name} | "
            f"{self.start_date}..{self.end_date}"
        )


def build_tasks(
    start_date:  date,
    end_date:    date,
    state:       Optional[str]   = None,
    game_type:   Optional[str]   = None,
    source_name: Optional[str]   = None,
) -> list[FetchTask]:
    """
    Build the complete list of FetchTasks for a date range.

    - Respects job lifecycle windows (active_start_date / active_end_date).
    - Respects source coverage windows (source_min_year / source_max_year).
    - Returns tasks sorted by: state, game_type, draw_time, source_priority.
    """
    states = [state.upper()] if state else get_all_states()
    tasks: list[FetchTask] = []

    for s in states:
        jobs = get_jobs_for_state(s, game_type=game_type)
        for job in jobs:
            # Clip task date range to job lifecycle window
            task_start = _clip_start(start_date, job)
            task_end   = _clip_end(end_date, job)
            if task_start > task_end:
                continue

            mappings = get_source_mappings_for_job(job, source_name=source_name)
            for mapping in mappings:
                # Clip further to source coverage window
                src_start = _source_clip_start(task_start, mapping)
                src_end   = _source_clip_end(task_end, mapping)
                if src_start > src_end:
                    continue
                tasks.append(FetchTask(
                    mapping=mapping,
                    start_date=src_start,
                    end_date=src_end,
                ))

    # Sort: state, game, draw_time, source_priority
    tasks.sort(key=lambda t: (
        t.mapping.job_def.state,
        t.mapping.job_def.game_type,
        t.mapping.job_def.draw_time,
        t.mapping.source_priority,
    ))
    return tasks


def build_tasks_for_state(
    state:       str,
    start_date:  date,
    end_date:    date,
    game_type:   Optional[str] = None,
    source_name: Optional[str] = None,
) -> list[FetchTask]:
    return build_tasks(start_date, end_date, state=state,
                       game_type=game_type, source_name=source_name)


def build_latest_tasks(
    state:       str,
    days:        int            = 7,
    game_type:   Optional[str] = None,
    source_name: Optional[str] = None,
) -> list[FetchTask]:
    """Build tasks for the last N days (useful for daily refresh)."""
    from datetime import timedelta
    end   = date.today()
    start = end - timedelta(days=days)
    return build_tasks_for_state(state, start, end,
                                 game_type=game_type, source_name=source_name)


# ------------------------------------------------------------------
# Internal clipping helpers
# ------------------------------------------------------------------

def _clip_start(requested: date, job: DrawJobDef) -> date:
    clipped = requested
    if job.active_start_date and job.active_start_date > clipped:
        clipped = job.active_start_date
    if job.source_min_year:
        floor = date(job.source_min_year, 1, 1)
        if floor > clipped:
            clipped = floor
    return clipped


def _clip_end(requested: date, job: DrawJobDef) -> date:
    clipped = requested
    if job.active_end_date and job.active_end_date < clipped:
        clipped = job.active_end_date
    if job.source_max_year:
        ceil = date(job.source_max_year, 12, 31)
        if ceil < clipped:
            clipped = ceil
    return clipped


def _source_clip_start(requested: date, mapping: SourceJobMapping) -> date:
    min_year = mapping.source_min_year or (mapping.job_def.source_min_year or 2000)
    floor = date(min_year, 1, 1)
    return max(requested, floor)


def _source_clip_end(requested: date, mapping: SourceJobMapping) -> date:
    max_year = mapping.source_max_year or (mapping.job_def.source_max_year or 9999)
    ceil = date(min(max_year, 9999), 12, 31)
    return min(requested, ceil)
