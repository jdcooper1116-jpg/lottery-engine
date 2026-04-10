"""
lottery_engine/registry/definitions/florida.py

Florida Lottery — Pick 3 and Pick 4.

Draw schedule:
  Midday (~1:30 PM ET) and Evening (~9:45 PM ET), daily.
  Midday was added ~2000; Evening has run since the early 1990s.
  No night draw. Standard 2-draw state.

Game names on lottery.net:
  pick3: "pick-3"  (Florida uses "Pick 3" — straightforward)
  pick4: "pick-4"

Slug status: ESTIMATED — verify against live lottery.net URLs before
  running full backfill. Pattern based on Georgia reference + FL naming.
  Expected: /florida/pick-3-midday/numbers/{year}
"""
from datetime import date
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "FL",
    "state_name":     "Florida",
    "wave":           1,
    "tier":           "1A",
    "complexity":     "standard",
    "status":         "seeded",
    "games":          ["pick3", "pick4"],
    "draws_per_day":  2,
    "draw_times":     {"pick3": ["midday", "evening"], "pick4": ["midday", "evening"]},
    "game_names":     {"pick3": "Pick 3", "pick4": "Pick 4"},
    "slugs_verified": False,
    "notes":          "Standard 2-draw state. Slugs estimated from GA reference pattern.",
}

# ------------------------------------------------------------------
# Canonical job definitions
# ------------------------------------------------------------------
_FL_PICK3_MIDDAY = DrawJobDef(
    state="FL", game_type="pick3", draw_time="midday",
    draw_label="Florida Pick 3 Midday", schedule_version="v1",
    active_start_date=date(2000, 1, 1),  # approximate
    active_end_date=None, source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="~1:30 PM ET daily. Midday draw added circa 2000.",
)
_FL_PICK3_EVENING = DrawJobDef(
    state="FL", game_type="pick3", draw_time="evening",
    draw_label="Florida Pick 3 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="~9:45 PM ET daily.",
)
_FL_PICK4_MIDDAY = DrawJobDef(
    state="FL", game_type="pick4", draw_time="midday",
    draw_label="Florida Pick 4 Midday", schedule_version="v1",
    active_start_date=date(2000, 1, 1), active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="~1:30 PM ET daily.",
)
_FL_PICK4_EVENING = DrawJobDef(
    state="FL", game_type="pick4", draw_time="evening",
    draw_label="Florida Pick 4 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="~9:45 PM ET daily.",
)

JOB_DEFINITIONS: list[DrawJobDef] = [
    _FL_PICK3_MIDDAY, _FL_PICK3_EVENING,
    _FL_PICK4_MIDDAY, _FL_PICK4_EVENING,
]

# ------------------------------------------------------------------
# Source mappings
# Slugs are ESTIMATED. Verify /florida/pick-3-midday/numbers/2024
# resolves on lottery.net before running backfill.
# ------------------------------------------------------------------
SOURCE_MAPPINGS: list[SourceJobMapping] = [
    # ---- lottery.net (priority 1) ----
    SourceJobMapping(
        job_def=_FL_PICK3_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="florida", source_game_slug="pick-3-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: slug pattern derived from GA reference. Verify before backfill.",
    ),
    SourceJobMapping(
        job_def=_FL_PICK3_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="florida", source_game_slug="pick-3-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="florida", source_game_slug="pick-4-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="florida", source_game_slug="pick-4-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED",
    ),
    # ---- lotterycorner.com (priority 2) ----
    SourceJobMapping(
        job_def=_FL_PICK3_MIDDAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="florida", source_game_slug="pick-3",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_FL_PICK3_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="florida", source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_MIDDAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="florida", source_game_slug="pick-4",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="florida", source_game_slug="pick-4",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    # ---- lotteryusa.com (priority 3, recent only) ----
    SourceJobMapping(
        job_def=_FL_PICK3_MIDDAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="florida", source_game_slug="pick-3",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent dates only.",
    ),
    SourceJobMapping(
        job_def=_FL_PICK3_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="florida", source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent dates only.",
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_MIDDAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="florida", source_game_slug="pick-4",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent dates only.",
    ),
    SourceJobMapping(
        job_def=_FL_PICK4_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="florida", source_game_slug="pick-4",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent dates only.",
    ),
]
