"""
lottery_engine/registry/definitions/florida.py

Florida Lottery draw job definitions and source mappings.

Florida runs Pick 3 and Pick 4 with Midday and Evening draws.
Historical notes:
  - Midday draws were added later than Evening draws. Approximate
    midday introduction circa 2000 (source_min_year=2000 for midday).
  - Evening draws have run since early lottery history (1988+), but
    reliable source data starts around 2002.

Update active_start_date fields when exact dates are confirmed.
"""
from datetime import date
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

# ------------------------------------------------------------------
# Canonical job definitions
# ------------------------------------------------------------------
_FL_PICK3_MIDDAY = DrawJobDef(
    state="FL",
    game_type="pick3",
    draw_time="midday",
    draw_label="Florida Pick 3 Midday",
    schedule_version="v1",
    active_start_date=date(2000, 1, 1),   # approximate
    active_end_date=None,
    source_min_year=2002,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="midday",
    notes="~1:30 PM ET daily. Midday draw added circa 2000.",
)

_FL_PICK3_EVENING = DrawJobDef(
    state="FL",
    game_type="pick3",
    draw_time="evening",
    draw_label="Florida Pick 3 Evening",
    schedule_version="v1",
    active_start_date=None,
    active_end_date=None,
    source_min_year=2002,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="evening",
    notes="~9:45 PM ET daily.",
)

_FL_PICK4_MIDDAY = DrawJobDef(
    state="FL",
    game_type="pick4",
    draw_time="midday",
    draw_label="Florida Pick 4 Midday",
    schedule_version="v1",
    active_start_date=date(2000, 1, 1),   # approximate
    active_end_date=None,
    source_min_year=2002,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="midday",
    notes="~1:30 PM ET daily.",
)

_FL_PICK4_EVENING = DrawJobDef(
    state="FL",
    game_type="pick4",
    draw_time="evening",
    draw_label="Florida Pick 4 Evening",
    schedule_version="v1",
    active_start_date=None,
    active_end_date=None,
    source_min_year=2002,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="evening",
    notes="~9:45 PM ET daily.",
)

JOB_DEFINITIONS: list[DrawJobDef] = [
    _FL_PICK3_MIDDAY,
    _FL_PICK3_EVENING,
    _FL_PICK4_MIDDAY,
    _FL_PICK4_EVENING,
]

# ------------------------------------------------------------------
# Source mappings
# ------------------------------------------------------------------
SOURCE_MAPPINGS: list[SourceJobMapping] = [
    # ---- lottery.net (priority 1) ----
    SourceJobMapping(
        job_def=_FL_PICK3_MIDDAY,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="florida",
        source_game_slug="pick-3",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/florida/pick-3/winning-numbers/{year}/{month:02d}",
        source_min_year=2002,
    ),
    SourceJobMapping(
        job_def=_FL_PICK3_EVENING,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="florida",
        source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/florida/pick-3/winning-numbers/{year}/{month:02d}",
        source_min_year=2002,
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_MIDDAY,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="florida",
        source_game_slug="pick-4",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/florida/pick-4/winning-numbers/{year}/{month:02d}",
        source_min_year=2002,
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_EVENING,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="florida",
        source_game_slug="pick-4",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/florida/pick-4/winning-numbers/{year}/{month:02d}",
        source_min_year=2002,
    ),

    # ---- lotterycorner.com (priority 2) ----
    SourceJobMapping(
        job_def=_FL_PICK3_MIDDAY,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="florida",
        source_game_slug="pick-3",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/florida/pick-3/{year}-{month:02d}.html",
        source_min_year=2005,
    ),
    SourceJobMapping(
        job_def=_FL_PICK3_EVENING,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="florida",
        source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/florida/pick-3/{year}-{month:02d}.html",
        source_min_year=2005,
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_MIDDAY,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="florida",
        source_game_slug="pick-4",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/florida/pick-4/{year}-{month:02d}.html",
        source_min_year=2005,
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_EVENING,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="florida",
        source_game_slug="pick-4",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/florida/pick-4/{year}-{month:02d}.html",
        source_min_year=2005,
    ),

    # ---- lotteryusa.com (priority 3, recent only) ----
    SourceJobMapping(
        job_def=_FL_PICK3_MIDDAY,
        source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="florida",
        source_game_slug="pick-3",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/florida/pick-3/",
        source_min_year=2018,
    ),
    SourceJobMapping(
        job_def=_FL_PICK3_EVENING,
        source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="florida",
        source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/florida/pick-3/",
        source_min_year=2018,
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_MIDDAY,
        source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="florida",
        source_game_slug="pick-4",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/florida/pick-4/",
        source_min_year=2018,
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_EVENING,
        source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="florida",
        source_game_slug="pick-4",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/florida/pick-4/",
        source_min_year=2018,
    ),
]
