"""
lottery_engine/registry/definitions/pennsylvania.py

Pennsylvania Lottery — Pick 3 and Pick 4.

DRAW SCHEDULE:
  Pennsylvania officially calls the daytime draw "Day" (not "Midday").
  Day draw:     ~1:35 PM ET  — canonical draw_time = "midday" (consistent with GA/FL)
  Evening draw: ~6:59 PM ET  — canonical draw_time = "evening"

SLUG CORRECTION (2025-04-11):
  lottery.net uses "Day" in the slug, not "Midday".
  Confirmed live URLs:
    https://www.lottery.net/pennsylvania/pick-3-day/numbers/2024   ✓
    https://www.lottery.net/pennsylvania/pick-3-evening/numbers/2024  ✓
    https://www.lottery.net/pennsylvania/pick-4-day/numbers/2024   ✓
    https://www.lottery.net/pennsylvania/pick-4-evening/numbers/2024  ✓
  BROKEN (404) — do not use:
    /pennsylvania/pick-3-midday/...   (404)
    /pennsylvania/pick-4-midday/...   (404)

All four lottery.net slugs are now slug_verified=True.
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
    # Pennsylvania officially calls draws "Day" and "Evening", not "Midday"
    "game_names":     {"pick3": "Pick 3", "pick4": "Pick 4"},
    "draw_labels":    {"midday": "Day", "evening": "Evening"},
    "slugs_verified": True,   # all four lottery.net slugs confirmed 2025-04-11
    "notes": (
        "PA uses 'Day' not 'Midday' for daytime draws. "
        "lottery.net slugs are pick-3-day / pick-4-day (not pick-3-midday). "
        "Draw time is 1:35 PM ET. Canonical draw_time='midday' kept for "
        "cross-state consistency with GA (12:29 PM) and FL (~1:30 PM)."
    ),
}

# ------------------------------------------------------------------
# Canonical job definitions
# draw_label uses "Day" to match PA official naming.
# draw_time uses "midday" canonical slot for cross-state consistency.
# ------------------------------------------------------------------
_PA_PICK3_DAY = DrawJobDef(
    state="PA", game_type="pick3", draw_time="midday",
    draw_label="Pennsylvania Pick 3 Day",   # "Day" per PA official name
    schedule_version="v1",
    active_start_date=date(2002, 1, 1),     # approximate; reliable data from ~2002
    active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="1:35 PM ET. PA officially calls this 'Day' draw, not 'Midday'. "
          "lottery.net slug is pick-3-day.",
)
_PA_PICK3_EVENING = DrawJobDef(
    state="PA", game_type="pick3", draw_time="evening",
    draw_label="Pennsylvania Pick 3 Evening",
    schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="6:59 PM ET daily.",
)
_PA_PICK4_DAY = DrawJobDef(
    state="PA", game_type="pick4", draw_time="midday",
    draw_label="Pennsylvania Pick 4 Day",   # "Day" per PA official name
    schedule_version="v1",
    active_start_date=date(2002, 1, 1),
    active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="1:35 PM ET. PA officially calls this 'Day' draw, not 'Midday'. "
          "lottery.net slug is pick-4-day.",
)
_PA_PICK4_EVENING = DrawJobDef(
    state="PA", game_type="pick4", draw_time="evening",
    draw_label="Pennsylvania Pick 4 Evening",
    schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="6:59 PM ET daily.",
)

JOB_DEFINITIONS: list[DrawJobDef] = [
    _PA_PICK3_DAY,
    _PA_PICK3_EVENING,
    _PA_PICK4_DAY,
    _PA_PICK4_EVENING,
]

# ------------------------------------------------------------------
# Source mappings — lottery.net slugs confirmed 2025-04-11
# Key lesson: PA uses "day" not "midday" in lottery.net slugs.
# ------------------------------------------------------------------
SOURCE_MAPPINGS: list[SourceJobMapping] = [
    # ── lottery.net (priority 1) — all slugs verified ──────────────────
    SourceJobMapping(
        job_def=_PA_PICK3_DAY,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="pennsylvania",
        source_game_slug="pick-3-day",          # CONFIRMED: /pennsylvania/pick-3-day/numbers/2024
        source_draw_time_label="Day",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002,
        slug_verified=True,
        notes="Verified 2025-04-11. PA uses 'Day' not 'Midday'. "
              "pick-3-midday is a 404 — do not revert.",
    ),
    SourceJobMapping(
        job_def=_PA_PICK3_EVENING,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="pennsylvania",
        source_game_slug="pick-3-evening",      # CONFIRMED: works
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002,
        slug_verified=True,
        notes="Verified 2025-04-11.",
    ),
    SourceJobMapping(
        job_def=_PA_PICK4_DAY,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="pennsylvania",
        source_game_slug="pick-4-day",          # CONFIRMED: /pennsylvania/pick-4-day/numbers/2024
        source_draw_time_label="Day",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002,
        slug_verified=True,
        notes="Verified 2025-04-11. Fixes 404 caused by pick-4-midday slug.",
    ),
    SourceJobMapping(
        job_def=_PA_PICK4_EVENING,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="pennsylvania",
        source_game_slug="pick-4-evening",      # CONFIRMED: works
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002,
        slug_verified=True,
        notes="Verified 2025-04-11.",
    ),
    # ── lotterycorner.com (priority 2) ─────────────────────────────────
    # lotterycorner uses "midday" in their own URL path, even though
    # PA officially calls it "Day". This is a source-specific label difference.
    SourceJobMapping(
        job_def=_PA_PICK3_DAY,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="pa",                 # lotterycorner uses state abbreviation
        source_game_slug="pick-3-midday",       # lotterycorner uses "midday" in their own path
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005,
        slug_verified=False,
        notes="ESTIMATED: lotterycorner may use 'pa' abbreviation and 'midday' label. Verify.",
    ),
    SourceJobMapping(
        job_def=_PA_PICK3_EVENING,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="pa",
        source_game_slug="pick-3-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005,
        slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_PA_PICK4_DAY,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="pa",
        source_game_slug="pick-4-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005,
        slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_PA_PICK4_EVENING,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="pa",
        source_game_slug="pick-4-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005,
        slug_verified=False,
        notes="ESTIMATED",
    ),
    # ── lotteryusa.com (priority 3, recent only) ────────────────────────
    SourceJobMapping(
        job_def=_PA_PICK3_DAY,
        source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="pennsylvania",
        source_game_slug="midday-pick-3",       # lotteryusa uses "midday-pick-3" path
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018,
        slug_verified=False,
        notes="ESTIMATED. lotteryusa uses 'midday-pick-3' per search results.",
    ),
    SourceJobMapping(
        job_def=_PA_PICK3_EVENING,
        source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="pennsylvania",
        source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018,
        slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_PA_PICK4_DAY,
        source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="pennsylvania",
        source_game_slug="midday-pick-4",       # lotteryusa uses "midday-pick-4" path
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018,
        slug_verified=False,
        notes="ESTIMATED. lotteryusa uses 'midday-pick-4' per search results.",
    ),
    SourceJobMapping(
        job_def=_PA_PICK4_EVENING,
        source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="pennsylvania",
        source_game_slug="pick-4",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018,
        slug_verified=False,
        notes="ESTIMATED",
    ),
]
