"""
lottery_engine/registry/loader.py
Query interface over the in-memory registry.
All filtering happens in Python over the imported definition lists.
No DB access. DB persistence is handled by seed.py.
"""
from datetime import date
from typing import Optional
from .models import DrawJobDef, SourceJobMapping
from .definitions import ALL_JOB_DEFINITIONS, ALL_SOURCE_MAPPINGS


def get_active_jobs(target_date: Optional[date] = None) -> list[DrawJobDef]:
    """
    Return all active job definitions, optionally filtered to those
    valid on target_date using lifecycle window fields.
    """
    if target_date is None:
        return [j for j in ALL_JOB_DEFINITIONS if j.is_active]
    return [j for j in ALL_JOB_DEFINITIONS if j.active_on(target_date)]


def get_jobs_for_state(
    state: str,
    game_type: Optional[str] = None,
    target_date: Optional[date] = None,
) -> list[DrawJobDef]:
    jobs = [j for j in get_active_jobs(target_date) if j.state == state.upper()]
    if game_type:
        jobs = [j for j in jobs if j.game_type == game_type.lower()]
    return jobs


def get_jobs_covering_year(state: str, game_type: str, year: int) -> list[DrawJobDef]:
    """Return jobs that cover a given historical year."""
    return [
        j for j in ALL_JOB_DEFINITIONS
        if j.state == state.upper()
        and j.game_type == game_type.lower()
        and j.is_active
        and j.covers_year(year)
    ]


def get_source_mappings_for_job(
    job: DrawJobDef,
    source_name: Optional[str] = None,
) -> list[SourceJobMapping]:
    """
    Return source mappings for a job, optionally filtered by source_name.
    Results sorted by source_priority ascending (primary first).
    """
    mappings = [
        m for m in ALL_SOURCE_MAPPINGS
        if m.job_def.state == job.state
        and m.job_def.game_type == job.game_type
        and m.job_def.draw_time == job.draw_time
        and m.job_def.schedule_version == job.schedule_version
        and m.is_enabled
    ]
    if source_name:
        mappings = [m for m in mappings if m.source_name == source_name]
    return sorted(mappings, key=lambda m: m.source_priority)


def get_all_states() -> list[str]:
    return sorted(set(j.state for j in ALL_JOB_DEFINITIONS if j.is_active))


def get_game_types_for_state(state: str) -> list[str]:
    return sorted(set(
        j.game_type for j in ALL_JOB_DEFINITIONS
        if j.state == state.upper() and j.is_active
    ))


def get_all_source_mappings_for_state(
    state: str,
    source_name: Optional[str] = None,
    target_year: Optional[int] = None,
) -> list[SourceJobMapping]:
    """All mappings for a state, optionally filtered by source and year."""
    mappings = [
        m for m in ALL_SOURCE_MAPPINGS
        if m.job_def.state == state.upper()
        and m.is_enabled
    ]
    if source_name:
        mappings = [m for m in mappings if m.source_name == source_name]
    if target_year:
        mappings = [m for m in mappings if m.covers_year(target_year)]
    return sorted(mappings, key=lambda m: (m.job_def.game_type, m.source_priority))
