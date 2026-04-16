"""
lottery_engine/query/service.py

The public query interface. All consumer apps (dream-number app, admin tools,
API routes) call only these functions. No scraping logic here.

All functions open their own DB connection. For batch operations, pass
an existing connection via the conn= parameter to share a transaction.
"""
from __future__ import annotations
import logging
import sqlite3
from datetime import date, timedelta
from typing import Optional

from db.connection import get_connection, get_db_path
from query.models import (
    QueryFilters,
    DrawRecord, MatchHit, CoverageGap, CandidateResult,
    DateRangeRequest, DateRangeResponse,
    WindowSearchRequest, WindowSearchResponse,
    CandidateMatchRequest, CandidateMatchResponse,
    DreamBacktestRequest, DreamBacktestResponse,
    BatchBacktestRequest, BatchBacktestResponse,
)
from query.match_engine import filter_draws_by_candidates
from query.coverage_checker import get_coverage_gaps

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# get_draws_for_date_range
# ------------------------------------------------------------------

def get_draws_for_date_range(req: DateRangeRequest) -> DateRangeResponse:
    """All draws for a state/game within an inclusive date range."""
    with get_connection() as conn:
        draws = _fetch_draws(
            conn,
            state=req.state,
            game_type=req.game_type,
            start_date=req.start_date.isoformat(),
            end_date=req.end_date.isoformat(),
            filters=req.filters,
        )
        gaps = get_coverage_gaps(
            conn, req.state, req.game_type,
            req.start_date, req.end_date,
            req.filters.draw_times,
        )
    return DateRangeResponse(
        request=req,
        draws=draws,
        total_count=len(draws),
        coverage_gaps=gaps,
    )


# ------------------------------------------------------------------
# search_results_by_window
# ------------------------------------------------------------------

def search_results_by_window(req: WindowSearchRequest) -> WindowSearchResponse:
    """All draws in a sliding window around anchor_date."""
    window_start = req.anchor_date - timedelta(days=req.lookbehind_days)
    window_end   = req.anchor_date + timedelta(days=req.lookahead_days)

    with get_connection() as conn:
        draws = _fetch_draws(
            conn,
            state=req.state,
            game_type=req.game_type,
            start_date=window_start.isoformat(),
            end_date=window_end.isoformat(),
            filters=req.filters,
        )
        gaps = get_coverage_gaps(
            conn, req.state, req.game_type,
            window_start, window_end,
            req.filters.draw_times,
        )
    return WindowSearchResponse(
        request=req,
        window_start=window_start,
        window_end=window_end,
        draws=draws,
        total_count=len(draws),
        coverage_gaps=gaps,
    )


# ------------------------------------------------------------------
# match_candidate_numbers
# ------------------------------------------------------------------

def match_candidate_numbers(req: CandidateMatchRequest) -> CandidateMatchResponse:
    """Find which candidates appeared as winning numbers in the range."""
    with get_connection() as conn:
        draws = _fetch_draws(
            conn,
            state=req.state,
            game_type=req.game_type,
            start_date=req.start_date.isoformat(),
            end_date=req.end_date.isoformat(),
            filters=req.filters,
        )

    hit_pairs = filter_draws_by_candidates(draws, req.candidates, req.filters.match_mode)
    hits = [
        MatchHit(
            candidate=candidate,
            draw_date=draw.draw_date,
            draw_time=draw.draw_time,
            winning_number=draw.winning_number,
            match_type=req.filters.match_mode,
            is_verified=draw.is_verified,
            canonical_key=draw.canonical_key,
            source_name=draw.source_name,
        )
        for candidate, draw in hit_pairs
    ]
    # Sort hits by date then draw_time
    hits.sort(key=lambda h: (h.draw_date, h.draw_time))

    candidates_with_hits    = sorted(set(h.candidate for h in hits))
    candidates_without_hits = sorted(set(req.candidates) - set(candidates_with_hits))

    return CandidateMatchResponse(
        request=req,
        hits=hits,
        hit_count=len(hits),
        candidates_with_hits=candidates_with_hits,
        candidates_without_hits=candidates_without_hits,
    )


# ------------------------------------------------------------------
# backtest_numbers  (single dream record)
# ------------------------------------------------------------------

def backtest_numbers(req: DreamBacktestRequest) -> DreamBacktestResponse:
    """
    Full backtest for a single dream record.
    Primary entry point for the dream-number app.

    Supports match_mode values in req.filters.match_mode:
      "exact" / "straight" — digit-for-digit match (same position)
      "box"                 — any permutation of the candidate's digits
      "digit"               — every digit in candidate appears in winning
      "pair"                — any consecutive 2-digit pair matches
    """
    window_start = req.anchor_date
    window_end   = req.anchor_date + timedelta(days=req.lookahead_days)
    match_mode   = req.filters.match_mode

    with get_connection() as conn:
        draws = _fetch_draws(
            conn,
            state=req.state,
            game_type=req.game_type,
            start_date=window_start.isoformat(),
            end_date=window_end.isoformat(),
            filters=req.filters,
        )
        gaps = get_coverage_gaps(
            conn, req.state, req.game_type,
            window_start, window_end,
            req.filters.draw_times,
        )

    coverage_complete = len(gaps) == 0

    hit_pairs = filter_draws_by_candidates(draws, req.candidates, match_mode)
    hits = [
        MatchHit(
            candidate=candidate,
            draw_date=draw.draw_date,
            draw_time=draw.draw_time,
            winning_number=draw.winning_number,
            match_type=match_mode,
            is_verified=draw.is_verified,
            canonical_key=draw.canonical_key,
            source_name=draw.source_name,
        )
        for candidate, draw in hit_pairs
    ]
    hits.sort(key=lambda h: (h.draw_date, h.draw_time))

    hit_dates      = sorted(set(h.draw_date for h in hits))
    hit_draw_times = [h.draw_time for h in hits]
    summary        = _build_summary(req, hits, window_start, window_end, match_mode)

    # --- build per-candidate results ----------------------------------------
    candidate_results = _build_candidate_results(
        req.candidates, hits, coverage_complete, len(draws)
    )
    # -------------------------------------------------------------------------

    return DreamBacktestResponse(
        request=req,
        window_start=window_start,
        window_end=window_end,
        all_draws=draws,
        hits=hits,
        hit_count=len(hits),
        hit_dates=hit_dates,
        hit_draw_times=hit_draw_times,
        coverage_gaps=gaps,
        summary=summary,
        match_mode=match_mode,
        draws_searched=len(draws),
        coverage_complete=coverage_complete,
        candidate_results=candidate_results,
    )


# ------------------------------------------------------------------
# batch_backtest  (multiple dream records)
# ------------------------------------------------------------------

def batch_backtest(req: BatchBacktestRequest) -> BatchBacktestResponse:
    """
    Run multiple backtest jobs, sharing a single DB connection.
    Efficient for the dream-number app processing a full dream log.
    """
    results: list[DreamBacktestResponse] = []
    total_hits    = 0
    total_draws   = 0
    jobs_with_hits = 0

    # Group jobs by (state, game_type) to pre-fetch date ranges in bulk
    with get_connection() as conn:
        for job in req.jobs:
            window_start = job.anchor_date
            window_end   = job.anchor_date + timedelta(days=job.lookahead_days)
            match_mode   = job.filters.match_mode

            draws = _fetch_draws(
                conn,
                state=job.state,
                game_type=job.game_type,
                start_date=window_start.isoformat(),
                end_date=window_end.isoformat(),
                filters=job.filters,
            )
            gaps = get_coverage_gaps(
                conn, job.state, job.game_type,
                window_start, window_end,
                job.filters.draw_times,
            )

            coverage_complete = len(gaps) == 0

            hit_pairs = filter_draws_by_candidates(draws, job.candidates, match_mode)
            hits = [
                MatchHit(
                    candidate=c,
                    draw_date=d.draw_date,
                    draw_time=d.draw_time,
                    winning_number=d.winning_number,
                    match_type=match_mode,
                    is_verified=d.is_verified,
                    canonical_key=d.canonical_key,
                    source_name=d.source_name,
                )
                for c, d in hit_pairs
            ]
            hits.sort(key=lambda h: (h.draw_date, h.draw_time))

            hit_dates      = sorted(set(h.draw_date for h in hits))
            hit_draw_times = [h.draw_time for h in hits]

            candidate_results = _build_candidate_results(
                job.candidates, hits, coverage_complete, len(draws)
            )

            resp = DreamBacktestResponse(
                request=job,
                window_start=window_start,
                window_end=window_end,
                all_draws=draws,
                hits=hits,
                hit_count=len(hits),
                hit_dates=hit_dates,
                hit_draw_times=hit_draw_times,
                coverage_gaps=gaps,
                summary=_build_summary(job, hits, window_start, window_end, match_mode),
                match_mode=match_mode,
                draws_searched=len(draws),
                coverage_complete=coverage_complete,
                candidate_results=candidate_results,
            )
            results.append(resp)
            total_hits    += len(hits)
            total_draws   += len(draws)
            if hits:
                jobs_with_hits += 1

    agg = (
        f"{total_hits} total hits across {len(req.jobs)} jobs "
        f"({jobs_with_hits} jobs had at least one hit). "
        f"{total_draws} draws searched."
    )
    return BatchBacktestResponse(
        results=results,
        total_hits=total_hits,
        total_draws_searched=total_draws,
        jobs_with_hits=jobs_with_hits,
        aggregate_summary=agg,
    )


# ------------------------------------------------------------------
# get_latest_results
# ------------------------------------------------------------------

def get_latest_results(
    state: str,
    game_type: str,
    n: int = 7,
    filters: Optional[QueryFilters] = None,
) -> list[DrawRecord]:
    """Most recent n draw results for a state/game."""
    filters = filters or QueryFilters()
    with get_connection() as conn:
        sql, params = _build_query(state, game_type, filters=filters)
        sql += " ORDER BY draw_date DESC, draw_time DESC LIMIT ?"
        params.append(n)
        rows = conn.execute(sql, params).fetchall()
    return [DrawRecord.from_row(r) for r in rows]


# ------------------------------------------------------------------
# get_schedule_for_date
# ------------------------------------------------------------------

def get_schedule_for_date(state: str, target_date: date) -> list:
    """
    Which draws were scheduled for this state on target_date.
    Delegates to the registry loader.
    """
    from registry.loader import get_jobs_for_state
    return get_jobs_for_state(state, target_date=target_date)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _fetch_draws(
    conn: sqlite3.Connection,
    state: str,
    game_type: str,
    start_date: str,
    end_date: str,
    filters: Optional[QueryFilters] = None,
) -> list[DrawRecord]:
    filters = filters or QueryFilters()
    sql, params = _build_query(state, game_type, filters=filters)
    sql += " AND draw_date BETWEEN ? AND ? ORDER BY draw_date, draw_time"
    params.extend([start_date, end_date])
    rows = conn.execute(sql, params).fetchall()
    return [DrawRecord.from_row(r) for r in rows]


def _build_query(
    state: str,
    game_type: str,
    filters: Optional[QueryFilters] = None,
) -> tuple[str, list]:
    """Build the base SELECT with filter clauses."""
    filters = filters or QueryFilters()
    sql = """
        SELECT canonical_key, state, game_type, draw_date, draw_time,
               winning_number, digit_count, sorted_digits,
               is_verified, has_conflict,
               accepted_from_source, accepted_source_priority
        FROM draws
        WHERE state=? AND game_type=?
    """
    params: list = [state.upper(), game_type.lower()]

    if filters.draw_times:
        placeholders = ",".join("?" * len(filters.draw_times))
        sql += f" AND draw_time IN ({placeholders})"
        params.extend(filters.draw_times)

    if filters.include_verified_only:
        sql += " AND is_verified=1"
    elif not filters.include_unverified:
        sql += " AND is_verified=1"

    if filters.exclude_conflicts:
        sql += " AND has_conflict=0"

    if filters.source_name:
        sql += " AND accepted_from_source=?"
        params.append(filters.source_name)

    return sql, params


def _build_summary(
    req: DreamBacktestRequest,
    hits: list[MatchHit],
    window_start: date,
    window_end: date,
    match_mode: str = "exact",
) -> str:
    label    = f" [{req.label}]" if req.label else ""
    mode_tag = f" (mode={match_mode})"
    if not hits:
        return (
            f"{req.state} {req.game_type}{label}{mode_tag}: "
            f"0 hits in {req.lookahead_days}-day window "
            f"({window_start} to {window_end}). "
            f"Candidates: {', '.join(req.candidates)}."
        )
    hit_parts = [
        f"{h.candidate}→{h.winning_number} on {h.draw_date} {h.draw_time}"
        for h in hits
    ]
    return (
        f"{req.state} {req.game_type}{label}{mode_tag}: "
        f"{len(hits)} hit(s) in {req.lookahead_days}-day window "
        f"({window_start} to {window_end}): "
        + "; ".join(hit_parts) + "."
    )


def _build_candidate_results(
    candidates: list[str],
    hits: list[MatchHit],
    coverage_complete: bool,
    draws_searched: int,
) -> list[CandidateResult]:
    """
    Build per-candidate diagnosis: did it hit, and if not, why not.

    status:
      "hit"      — at least one matching draw found
      "no_match" — no draw matched

    miss_reason (when status == "no_match"):
      "no_draw_matched"  — draws were searched, none matched
      "window_has_gaps"  — window has coverage gaps, result is inconclusive
      "no_draws_in_window" — window returned 0 draws (nothing to search)
    """
    # Build a lookup: candidate -> list of hits
    hits_by_candidate: dict[str, list[MatchHit]] = {}
    for h in hits:
        hits_by_candidate.setdefault(h.candidate, []).append(h)

    results: list[CandidateResult] = []
    for c in candidates:
        c_sorted   = "".join(sorted(c))
        c_hits     = hits_by_candidate.get(c, [])
        hit        = bool(c_hits)

        if hit:
            status      = "hit"
            miss_reason = ""
        else:
            status = "no_match"
            if draws_searched == 0:
                miss_reason = "no_draws_in_window"
            elif not coverage_complete:
                miss_reason = "window_has_gaps"
            else:
                miss_reason = "no_draw_matched"

        results.append(CandidateResult(
            candidate=c,
            candidate_sorted=c_sorted,
            status=status,
            hit_count=len(c_hits),
            hits=c_hits,
            coverage_complete=coverage_complete,
            miss_reason=miss_reason,
        ))

    return results
    