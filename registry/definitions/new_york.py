"""
lottery_engine/registry/definitions/new_york.py

New York Lottery — Numbers (Pick 3) and Win 4 (Pick 4).

IMPORTANT: New York uses non-standard game names.
  pick3 equivalent = "Numbers"   (drawn since 1970s)
  pick4 equivalent = "Win 4"     (drawn since 1980s)

Draw schedule: Midday (~2:30 PM ET) and Evening (~10:30 PM ET), daily.
No morning or night draw. Standard 2-draw state.

lottery.net slug notes:
  The slug for NY Numbers is likely "numbers-midday" / "numbers-evening".
  The slug for Win 4 is likely "win-4-midday" / "win-4-evening".
  All ESTIMATED — verify URLs:
    https://www.lottery.net/new-york/numbers-midday/numbers/{year}
    https://www.lottery.net/new-york/win-4-midday/numbers/{year}
  before running backfill.

lotterycorner.com may use "numbers" and "win-4" as game slugs.
lotteryusa.com may use "numbers" and "win-4".
"""
from datetime import date
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "NY",
    "state_name":     "New York",
    "wave":           1,
    "tier":           "1A",
    "complexity":     "standard",
    "status":         "seeded",
    "games":          ["pick3", "pick4"],
    "draws_per_day":  2,
    "draw_times":     {"pick3": ["midday", "evening"], "pick4": ["midday", "evening"]},
    "game_names":     {"pick3": "Numbers", "pick4": "Win 4"},
    "slugs_verified": False,
    "notes": (
        "NY uses 'Numbers' for pick3 and 'Win 4' for pick4. "
        "Non-standard names require careful slug verification. "
        "lottery.net state slug is likely 'new-york'."
    ),
}

# ------------------------------------------------------------------
_NY_PICK3_MIDDAY = DrawJobDef(
    state="NY", game_type="pick3", draw_time="midday",
    draw_label="New York Numbers Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="~2:30 PM ET. NY pick3 game is called 'Numbers'.",
)
_NY_PICK3_EVENING = DrawJobDef(
    state="NY", game_type="pick3", draw_time="evening",
    draw_label="New York Numbers Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="~10:30 PM ET.",
)
_NY_PICK4_MIDDAY = DrawJobDef(
    state="NY", game_type="pick4", draw_time="midday",
    draw_label="New York Win 4 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="~2:30 PM ET. NY pick4 game is called 'Win 4'.",
)
_NY_PICK4_EVENING = DrawJobDef(
    state="NY", game_type="pick4", draw_time="evening",
    draw_label="New York Win 4 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="~10:30 PM ET.",
)

JOB_DEFINITIONS: list[DrawJobDef] = [
    _NY_PICK3_MIDDAY, _NY_PICK3_EVENING,
    _NY_PICK4_MIDDAY, _NY_PICK4_EVENING,
]

SOURCE_MAPPINGS: list[SourceJobMapping] = [
    # ---- lottery.net (priority 1) ----
    # NY state slug on lottery.net is "new-york"
    # Numbers (pick3) slug is likely "numbers-midday" — VERIFY
    SourceJobMapping(
        job_def=_NY_PICK3_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="new-york", source_game_slug="numbers-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: NY 'Numbers' game. Check /new-york/numbers-midday/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_NY_PICK3_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="new-york", source_game_slug="numbers-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED",
    ),
    # Win 4 (pick4) slug is likely "win-4-midday" — VERIFY
    SourceJobMapping(
        job_def=_NY_PICK4_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="new-york", source_game_slug="win-4-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: NY 'Win 4' game. Check /new-york/win-4-midday/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_NY_PICK4_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="new-york", source_game_slug="win-4-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED",
    ),
    # ---- lotterycorner.com (priority 2) ----
    SourceJobMapping(
        job_def=_NY_PICK3_MIDDAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="new-york", source_game_slug="numbers",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_NY_PICK3_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="new-york", source_game_slug="numbers",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_NY_PICK4_MIDDAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="new-york", source_game_slug="win-4",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_NY_PICK4_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="new-york", source_game_slug="win-4",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    # ---- lotteryusa.com (priority 3) ----
    SourceJobMapping(
        job_def=_NY_PICK3_MIDDAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="new-york", source_game_slug="numbers",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent dates only.",
    ),
    SourceJobMapping(
        job_def=_NY_PICK3_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="new-york", source_game_slug="numbers",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent dates only.",
    ),
    SourceJobMapping(
        job_def=_NY_PICK4_MIDDAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="new-york", source_game_slug="win-4",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent dates only.",
    ),
    SourceJobMapping(
        job_def=_NY_PICK4_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="new-york", source_game_slug="win-4",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent dates only.",
    ),
]
