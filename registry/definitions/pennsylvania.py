"""
lottery_engine/registry/definitions/pennsylvania.py

Pennsylvania Lottery — Pick 3 and Pick 4.

Draw schedule: Midday (~1:35 PM ET) and Evening (~6:59 PM ET), daily.
Standard 2-draw state. Game names are straightforward "Pick 3" / "Pick 4".

Slug notes: ESTIMATED. Expected lottery.net slugs:
  /pennsylvania/pick-3-midday/numbers/{year}
  /pennsylvania/pick-4-midday/numbers/{year}
"""
from datetime import date
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "PA",
    "state_name":     "Pennsylvania",
    "wave":           1,
    "tier":           "1A",
    "complexity":     "standard",
    "status":         "seeded",
    "games":          ["pick3", "pick4"],
    "draws_per_day":  2,
    "draw_times":     {"pick3": ["midday", "evening"], "pick4": ["midday", "evening"]},
    "game_names":     {"pick3": "Pick 3", "pick4": "Pick 4"},
    "slugs_verified": False,
    "notes":          "Standard 2-draw state. Slugs estimated.",
}

_PA_PICK3_MIDDAY = DrawJobDef(
    state="PA", game_type="pick3", draw_time="midday",
    draw_label="Pennsylvania Pick 3 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="~1:35 PM ET daily.",
)
_PA_PICK3_EVENING = DrawJobDef(
    state="PA", game_type="pick3", draw_time="evening",
    draw_label="Pennsylvania Pick 3 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="~6:59 PM ET daily.",
)
_PA_PICK4_MIDDAY = DrawJobDef(
    state="PA", game_type="pick4", draw_time="midday",
    draw_label="Pennsylvania Pick 4 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="~1:35 PM ET daily.",
)
_PA_PICK4_EVENING = DrawJobDef(
    state="PA", game_type="pick4", draw_time="evening",
    draw_label="Pennsylvania Pick 4 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="~6:59 PM ET daily.",
)

JOB_DEFINITIONS: list[DrawJobDef] = [
    _PA_PICK3_MIDDAY, _PA_PICK3_EVENING,
    _PA_PICK4_MIDDAY, _PA_PICK4_EVENING,
]

def _ln(job, slug):
    return SourceJobMapping(
        job_def=job, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="pennsylvania", source_game_slug=slug,
        source_draw_time_label=job.draw_time.title(),
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False, notes="ESTIMATED",
    )

def _lc(job, slug):
    return SourceJobMapping(
        job_def=job, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="pennsylvania", source_game_slug=slug,
        source_draw_time_label=job.draw_time.title(),
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False, notes="ESTIMATED",
    )

def _lu(job, slug):
    return SourceJobMapping(
        job_def=job, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="pennsylvania", source_game_slug=slug,
        source_draw_time_label=job.draw_time.title(),
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False, notes="ESTIMATED. Recent only.",
    )

SOURCE_MAPPINGS: list[SourceJobMapping] = [
    _ln(_PA_PICK3_MIDDAY,  "pick-3-midday"),
    _ln(_PA_PICK3_EVENING, "pick-3-evening"),
    _ln(_PA_PICK4_MIDDAY,  "pick-4-midday"),
    _ln(_PA_PICK4_EVENING, "pick-4-evening"),
    _lc(_PA_PICK3_MIDDAY,  "pick-3"),
    _lc(_PA_PICK3_EVENING, "pick-3"),
    _lc(_PA_PICK4_MIDDAY,  "pick-4"),
    _lc(_PA_PICK4_EVENING, "pick-4"),
    _lu(_PA_PICK3_MIDDAY,  "pick-3"),
    _lu(_PA_PICK3_EVENING, "pick-3"),
    _lu(_PA_PICK4_MIDDAY,  "pick-4"),
    _lu(_PA_PICK4_EVENING, "pick-4"),
]
