"""
lottery_engine/query/models.py

All typed request, response, and filter dataclasses for the query layer.
These are the public contract between the query service and any consumer app.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# ------------------------------------------------------------------
# Filter surface — attached to every query request
# ------------------------------------------------------------------

@dataclass
class QueryFilters:
    draw_times:            Optional[list[str]] = None
    # None = all draw times; list of canonical enum values to restrict

    match_mode:            str                 = "exact"
    # "exact" | "box" | "digit" | "pair" | "triple" | "presence"

    include_verified_only: bool                = False
    # True = only rows where is_verified = 1

    include_unverified:    bool                = True
    # False = exclude is_verified=0 rows (only meaningful when include_verified_only=False)

    source_name:           Optional[str]       = None
    # None = all sources; restrict accepted_from_source to this value

    exclude_conflicts:     bool                = False
    # True = skip canonical rows where has_conflict = 1


# ------------------------------------------------------------------
# Core record types returned by every query
# ------------------------------------------------------------------

@dataclass
class DrawRecord:
    canonical_key:    str
    state:            str
    game_type:        str
    draw_date:        str          # YYYY-MM-DD string
    draw_time:        str          # canonical enum
    winning_number:   str
    digit_count:      int
    sorted_digits:    str
    is_verified:      bool
    has_conflict:     bool
    accepted_from_source: str
    accepted_source_priority: int

    # Convenience alias so callers can use draw.source_name or
    # draw.accepted_from_source interchangeably.  Both refer to the
    # source that provided the accepted canonical winning number.
    @property
    def source_name(self) -> str:
        return self.accepted_from_source

    @classmethod
    def from_row(cls, row) -> "DrawRecord":
        return cls(
            canonical_key=row["canonical_key"],
            state=row["state"],
            game_type=row["game_type"],
            draw_date=row["draw_date"],
            draw_time=row["draw_time"],
            winning_number=row["winning_number"],
            digit_count=row["digit_count"],
            sorted_digits=row["sorted_digits"],
            is_verified=bool(row["is_verified"]),
            has_conflict=bool(row["has_conflict"]),
            accepted_from_source=row["accepted_from_source"],
            accepted_source_priority=row["accepted_source_priority"],
        )


@dataclass
class MatchHit:
    candidate:        str
    draw_date:        str
    draw_time:        str
    winning_number:   str
    match_type:       str          # "exact" | "box" | "digit" etc.
    is_verified:      bool
    canonical_key:    str
    source_name:      str = ""     # accepted_from_source of the matched draw


@dataclass
class CoverageGap:
    draw_date:        str
    draw_time:        str
    coverage_status:  str          # "not_scraped" | "scrape_error"
    last_attempted_at: Optional[str]


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------

@dataclass
class DateRangeRequest:
    state:      str
    game_type:  str
    start_date: date
    end_date:   date
    filters:    QueryFilters = field(default_factory=QueryFilters)


@dataclass
class DateRangeResponse:
    request:        DateRangeRequest
    draws:          list[DrawRecord]
    total_count:    int
    coverage_gaps:  list[CoverageGap]


@dataclass
class WindowSearchRequest:
    state:           str
    game_type:       str
    anchor_date:     date
    lookahead_days:  int  = 7
    lookbehind_days: int  = 0
    filters:         QueryFilters = field(default_factory=QueryFilters)


@dataclass
class WindowSearchResponse:
    request:         WindowSearchRequest
    window_start:    date
    window_end:      date
    draws:           list[DrawRecord]
    total_count:     int
    coverage_gaps:   list[CoverageGap]


@dataclass
class CandidateMatchRequest:
    state:      str
    game_type:  str
    start_date: date
    end_date:   date
    candidates: list[str]
    filters:    QueryFilters = field(default_factory=QueryFilters)


@dataclass
class CandidateMatchResponse:
    request:                 CandidateMatchRequest
    hits:                    list[MatchHit]
    hit_count:               int
    candidates_with_hits:    list[str]
    candidates_without_hits: list[str]


@dataclass
class DreamBacktestRequest:
    state:           str
    game_type:       str
    anchor_date:     date          # the dream/log date itself
    lookahead_days:  int  = 7      # 7–10 configurable
    candidates:      list[str] = field(default_factory=list)
    filters:         QueryFilters = field(default_factory=QueryFilters)
    label:           str  = ""     # optional label for this dream record


@dataclass
class DreamBacktestResponse:
    request:          DreamBacktestRequest
    window_start:     date
    window_end:       date
    all_draws:        list[DrawRecord]
    hits:             list[MatchHit]
    hit_count:        int
    hit_dates:        list[str]
    hit_draw_times:   list[str]
    coverage_gaps:    list[CoverageGap]
    summary:          str


@dataclass
class BatchBacktestRequest:
    jobs: list[DreamBacktestRequest]
    # Each job is an independent dream-record backtest.
    # Jobs may span different states, game types, and anchor dates.


@dataclass
class BatchBacktestResponse:
    results:               list[DreamBacktestResponse]
    total_hits:            int
    total_draws_searched:  int
    jobs_with_hits:        int
    aggregate_summary:     str
