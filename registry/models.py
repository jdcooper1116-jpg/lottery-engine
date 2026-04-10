"""
lottery_engine/registry/models.py
Dataclass models for the registry layer.
These are Python-side representations of draw_job_definitions
and source_job_mappings. They are serialized to/from the DB by seed.py.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DrawJobDef:
    """
    One versioned draw job definition.
    Represents a single (state, game_type, draw_time) schedule entry
    with full lifecycle window support.
    """
    state:               str
    game_type:           str               # "pick3" | "pick4"
    draw_time:           str               # canonical DrawTime value
    draw_label:          str
    schedule_version:    str               = "v1"
    active_start_date:   Optional[date]    = None   # None = unknown / always active
    active_end_date:     Optional[date]    = None   # None = still active
    source_min_year:     Optional[int]     = None   # soft floor for historical scraping
    source_max_year:     Optional[int]     = None   # None = ongoing
    draw_days:           str               = "daily"
    canonical_time_key:  str               = ""     # auto-set to draw_time if empty
    notes:               str               = ""
    is_active:           bool              = True
    # Set by seed/loader after DB insert:
    db_id:               Optional[int]     = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.canonical_time_key:
            self.canonical_time_key = self.draw_time

    @property
    def is_valid_on(self) -> bool:
        """True if this job has no end date (still active)."""
        return self.active_end_date is None

    def active_on(self, target: date) -> bool:
        if not self.is_active:
            return False
        if self.active_start_date and target < self.active_start_date:
            return False
        if self.active_end_date and target > self.active_end_date:
            return False
        return True

    def covers_year(self, year: int) -> bool:
        if self.source_min_year and year < self.source_min_year:
            return False
        if self.source_max_year and year > self.source_max_year:
            return False
        return True


@dataclass
class SourceJobMapping:
    """
    Maps one DrawJobDef to one source's specific URL/slug structure.
    Decouples scraper URL knowledge from canonical job definitions.
    """
    job_def:                DrawJobDef
    source_name:            str
    source_priority:        int
    source_state_slug:      Optional[str]  = None
    source_game_slug:       Optional[str]  = None
    source_draw_time_label: Optional[str]  = None   # raw label this source uses
    url_template:           Optional[str]  = None
    source_min_year:        Optional[int]  = None
    source_max_year:        Optional[int]  = None
    is_enabled:             bool           = True
    slug_verified:          bool           = False  # True once confirmed on live site
    notes:                  str            = ""
    db_id:                  Optional[int]  = field(default=None, repr=False)

    def build_url(self, **kwargs) -> Optional[str]:
        """Interpolate url_template with given kwargs."""
        if not self.url_template:
            return None
        try:
            return self.url_template.format(
                state_slug=self.source_state_slug or "",
                game_slug=self.source_game_slug or "",
                **kwargs,
            )
        except KeyError:
            return self.url_template

    def covers_year(self, year: int) -> bool:
        min_y = self.source_min_year or (self.job_def.source_min_year or 2000)
        max_y = self.source_max_year or (self.job_def.source_max_year or 9999)
        return min_y <= year <= max_y
