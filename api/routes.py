"""
lottery_engine/api/routes.py

Thin FastAPI wrapper over query/service.py.
All business logic lives in the query layer.
Consumer apps can also import query/service.py directly as a Python library
without starting the HTTP server.

Start server:
    uvicorn api.routes:app --reload --port 8000
"""
from __future__ import annotations
from datetime import date
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from query.service import (
    get_draws_for_date_range,
    search_results_by_window,
    match_candidate_numbers,
    backtest_numbers,
    batch_backtest,
    get_latest_results,
    get_schedule_for_date,
)
from query.models import (
    QueryFilters,
    DateRangeRequest,
    WindowSearchRequest,
    CandidateMatchRequest,
    DreamBacktestRequest,
    BatchBacktestRequest,
)
from registry.loader import get_all_states, get_game_types_for_state
from registry.enums import SourceName, DrawTime
from orchestrator.coverage import get_coverage_stats
from db.connection import get_connection

app = FastAPI(
    title="Lottery Results Engine",
    description="State-aware historical lottery results engine for backtesting and querying.",
    version="2.0.0",
)


# ------------------------------------------------------------------
# Pydantic request bodies
# ------------------------------------------------------------------

class FilterParams(BaseModel):
    draw_times:            Optional[list[str]] = None
    match_mode:            str                 = "exact"
    include_verified_only: bool                = False
    include_unverified:    bool                = True
    source_name:           Optional[str]       = None
    exclude_conflicts:     bool                = False

    def to_filters(self) -> QueryFilters:
        return QueryFilters(
            draw_times=self.draw_times,
            match_mode=self.match_mode,
            include_verified_only=self.include_verified_only,
            include_unverified=self.include_unverified,
            source_name=self.source_name,
            exclude_conflicts=self.exclude_conflicts,
        )


class BacktestBody(BaseModel):
    state:          str
    game_type:      str
    anchor_date:    date
    lookahead_days: int                  = Field(default=7, ge=1, le=30)
    candidates:     list[str]            = Field(default_factory=list)
    filters:        FilterParams         = Field(default_factory=FilterParams)
    label:          str                  = ""


class BatchBacktestBody(BaseModel):
    jobs: list[BacktestBody]


class MatchBody(BaseModel):
    state:      str
    game_type:  str
    start_date: date
    end_date:   date
    candidates: list[str]
    filters:    FilterParams = Field(default_factory=FilterParams)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/states")
def list_states():
    return {"states": get_all_states()}


@app.get("/games")
def list_games(state: str):
    return {"state": state.upper(), "game_types": get_game_types_for_state(state)}


@app.get("/sources")
def list_sources():
    return {"sources": SourceName.values()}


@app.get("/draw-times")
def list_draw_times():
    return {"draw_times": DrawTime.values()}


@app.get("/draws")
def draws_range(
    state:      str,
    game_type:  str,
    start:      date,
    end:        date,
    draw_times: Optional[str] = Query(default=None, description="Comma-separated canonical draw times"),
    verified_only: bool = False,
    source_name:   Optional[str] = None,
    exclude_conflicts: bool = False,
):
    dt_list = [d.strip() for d in draw_times.split(",")] if draw_times else None
    req = DateRangeRequest(
        state=state.upper(), game_type=game_type.lower(),
        start_date=start, end_date=end,
        filters=QueryFilters(
            draw_times=dt_list,
            include_verified_only=verified_only,
            source_name=source_name,
            exclude_conflicts=exclude_conflicts,
        ),
    )
    resp = get_draws_for_date_range(req)
    return {
        "state":         resp.request.state,
        "game_type":     resp.request.game_type,
        "start_date":    resp.request.start_date.isoformat(),
        "end_date":      resp.request.end_date.isoformat(),
        "total_count":   resp.total_count,
        "draws":         [_draw_to_dict(d) for d in resp.draws],
        "coverage_gaps": [_gap_to_dict(g) for g in resp.coverage_gaps],
    }


@app.get("/draws/latest")
def latest_draws(state: str, game_type: str, n: int = 7):
    draws = get_latest_results(state.upper(), game_type.lower(), n)
    return {"draws": [_draw_to_dict(d) for d in draws]}


@app.get("/draws/window")
def window_search(
    state:        str,
    game_type:    str,
    anchor:       date,
    lookahead:    int = 7,
    lookbehind:   int = 0,
    draw_times:   Optional[str] = None,
    verified_only: bool = False,
):
    dt_list = [d.strip() for d in draw_times.split(",")] if draw_times else None
    req = WindowSearchRequest(
        state=state.upper(), game_type=game_type.lower(),
        anchor_date=anchor,
        lookahead_days=lookahead,
        lookbehind_days=lookbehind,
        filters=QueryFilters(draw_times=dt_list, include_verified_only=verified_only),
    )
    resp = search_results_by_window(req)
    return {
        "window_start":  resp.window_start.isoformat(),
        "window_end":    resp.window_end.isoformat(),
        "total_count":   resp.total_count,
        "draws":         [_draw_to_dict(d) for d in resp.draws],
        "coverage_gaps": [_gap_to_dict(g) for g in resp.coverage_gaps],
    }


@app.get("/draws/coverage")
def coverage_summary(state: str, game_type: Optional[str] = None):
    with get_connection() as conn:
        stats = get_coverage_stats(conn, state.upper(), game_type)
    return {"coverage": stats}


@app.post("/match")
def match(body: MatchBody):
    req = CandidateMatchRequest(
        state=body.state.upper(), game_type=body.game_type.lower(),
        start_date=body.start_date, end_date=body.end_date,
        candidates=body.candidates,
        filters=body.filters.to_filters(),
    )
    resp = match_candidate_numbers(req)
    return {
        "hit_count":               resp.hit_count,
        "candidates_with_hits":    resp.candidates_with_hits,
        "candidates_without_hits": resp.candidates_without_hits,
        "hits":                    [_hit_to_dict(h) for h in resp.hits],
    }


@app.post("/backtest")
def backtest(body: BacktestBody):
    req = DreamBacktestRequest(
        state=body.state.upper(), game_type=body.game_type.lower(),
        anchor_date=body.anchor_date,
        lookahead_days=body.lookahead_days,
        candidates=body.candidates,
        filters=body.filters.to_filters(),
        label=body.label,
    )
    resp = backtest_numbers(req)
    return {
        "window_start":   resp.window_start.isoformat(),
        "window_end":     resp.window_end.isoformat(),
        "hit_count":      resp.hit_count,
        "hit_dates":      resp.hit_dates,
        "hit_draw_times": resp.hit_draw_times,
        "summary":        resp.summary,
        "hits":           [_hit_to_dict(h) for h in resp.hits],
        "all_draws":      [_draw_to_dict(d) for d in resp.all_draws],
        "coverage_gaps":  [_gap_to_dict(g) for g in resp.coverage_gaps],
    }


@app.post("/backtest/batch")
def backtest_batch(body: BatchBacktestBody):
    jobs = [
        DreamBacktestRequest(
            state=j.state.upper(), game_type=j.game_type.lower(),
            anchor_date=j.anchor_date,
            lookahead_days=j.lookahead_days,
            candidates=j.candidates,
            filters=j.filters.to_filters(),
            label=j.label,
        )
        for j in body.jobs
    ]
    req  = BatchBacktestRequest(jobs=jobs)
    resp = batch_backtest(req)
    return {
        "total_hits":           resp.total_hits,
        "total_draws_searched": resp.total_draws_searched,
        "jobs_with_hits":       resp.jobs_with_hits,
        "aggregate_summary":    resp.aggregate_summary,
        "results": [
            {
                "label":        r.request.label,
                "anchor_date":  r.request.anchor_date.isoformat(),
                "window_start": r.window_start.isoformat(),
                "window_end":   r.window_end.isoformat(),
                "hit_count":    r.hit_count,
                "summary":      r.summary,
                "hits":         [_hit_to_dict(h) for h in r.hits],
            }
            for r in resp.results
        ],
    }


@app.get("/schedule")
def schedule(state: str, target_date: date):
    jobs = get_schedule_for_date(state.upper(), target_date)
    return {
        "state":       state.upper(),
        "date":        target_date.isoformat(),
        "scheduled_draws": [
            {
                "game_type":  j.game_type,
                "draw_time":  j.draw_time,
                "draw_label": j.draw_label,
                "active_start_date": j.active_start_date.isoformat() if j.active_start_date else None,
            }
            for j in jobs
        ],
    }


# ------------------------------------------------------------------
# Serialization helpers
# ------------------------------------------------------------------

def _draw_to_dict(d) -> dict:
    return {
        "canonical_key":          d.canonical_key,
        "state":                  d.state,
        "game_type":              d.game_type,
        "draw_date":              d.draw_date,
        "draw_time":              d.draw_time,
        "winning_number":         d.winning_number,
        "digit_count":            d.digit_count,
        "sorted_digits":          d.sorted_digits,
        "is_verified":            d.is_verified,
        "has_conflict":           d.has_conflict,
        "source_name":            d.source_name,
        "accepted_from_source":   d.accepted_from_source,
    }


def _hit_to_dict(h) -> dict:
    return {
        "candidate":      h.candidate,
        "draw_date":      h.draw_date,
        "draw_time":      h.draw_time,
        "winning_number": h.winning_number,
        "match_type":     h.match_type,
        "is_verified":    h.is_verified,
        "source_name":    h.source_name,
        "canonical_key":  h.canonical_key,
    }


def _gap_to_dict(g) -> dict:
    return {
        "draw_date":        g.draw_date,
        "draw_time":        g.draw_time,
        "coverage_status":  g.coverage_status,
        "last_attempted":   g.last_attempted_at,
    }
