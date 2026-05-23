"""
lottery_engine/registry/definitions/georgia.py

Georgia Lottery draw job definitions and source mappings.

Georgia runs Cash 3 (Pick 3) and Cash 4 (Pick 4).
Historical draw schedule:
  - Midday and Evening draws have run for the full recorded history.
  - A Night draw was added circa 2012 (exact date to be verified;
    active_start_date marked approximate with note).
  - source_min_year=2002 reflects the earliest data seen on lottery.net.

Slots verified against lottery.net as of 2024.
Update active_start_date fields when exact dates are confirmed.
"""
from datetime import date
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "GA",
    "state_name":     "Georgia",
    "wave":           1,
    "tier":           "1A",
    "complexity":     "moderate",
    "status":         "seeded",
    "games":          ["pick3", "pick4"],
    "draws_per_day":  3,
    "draw_times":     {"pick3": ["midday","evening","night"],
                       "pick4": ["midday","evening","night"]},
    "game_names":     {"pick3": "Cash 3", "pick4": "Cash 4"},
    "slugs_verified": True,
    "notes": (
        "Reference state. 3 draws/day. Night draw added ~2012. "
        "lottery.net slugs verified via live ingest. "
        "active_start_date for night draw is approximate."
    ),
}


# ------------------------------------------------------------------
# Canonical job definitions
# ------------------------------------------------------------------
_GA_PICK3_MIDDAY = DrawJobDef(
    state="GA",
    game_type="pick3",
    draw_time="midday",
    draw_label="Georgia Cash 3 Midday",
    schedule_version="v1",
    active_start_date=None,       # pre-2002, exact date unknown
    active_end_date=None,
    source_min_year=2002,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="midday",
    notes="~12:29 PM ET daily. Part of original Cash 3 schedule.",
)

_GA_PICK3_EVENING = DrawJobDef(
    state="GA",
    game_type="pick3",
    draw_time="evening",
    draw_label="Georgia Cash 3 Evening",
    schedule_version="v1",
    active_start_date=None,
    active_end_date=None,
    source_min_year=2002,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="evening",
    notes="~6:59 PM ET daily. Part of original Cash 3 schedule.",
)

_GA_PICK3_NIGHT = DrawJobDef(
    state="GA",
    game_type="pick3",
    draw_time="night",
    draw_label="Georgia Cash 3 Night",
    schedule_version="v1",
    active_start_date=date(2012, 1, 1),   # APPROXIMATE - verify with source data
    active_end_date=None,
    source_min_year=2012,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="night",
    notes="~11:34 PM ET daily. Added circa 2012. active_start_date is approximate.",
)

_GA_PICK4_MIDDAY = DrawJobDef(
    state="GA",
    game_type="pick4",
    draw_time="midday",
    draw_label="Georgia Cash 4 Midday",
    schedule_version="v1",
    active_start_date=None,
    active_end_date=None,
    source_min_year=2002,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="midday",
    notes="~12:29 PM ET daily.",
)

_GA_PICK4_EVENING = DrawJobDef(
    state="GA",
    game_type="pick4",
    draw_time="evening",
    draw_label="Georgia Cash 4 Evening",
    schedule_version="v1",
    active_start_date=None,
    active_end_date=None,
    source_min_year=2002,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="evening",
    notes="~6:59 PM ET daily.",
)

_GA_PICK4_NIGHT = DrawJobDef(
    state="GA",
    game_type="pick4",
    draw_time="night",
    draw_label="Georgia Cash 4 Night",
    schedule_version="v1",
    active_start_date=date(2012, 1, 1),   # APPROXIMATE
    active_end_date=None,
    source_min_year=2012,
    source_max_year=None,
    draw_days="daily",
    canonical_time_key="night",
    notes="~11:34 PM ET daily. Added circa 2012. active_start_date is approximate.",
)

JOB_DEFINITIONS: list[DrawJobDef] = [
    _GA_PICK3_MIDDAY,
    _GA_PICK3_EVENING,
    _GA_PICK3_NIGHT,
    _GA_PICK4_MIDDAY,
    _GA_PICK4_EVENING,
    _GA_PICK4_NIGHT,
]

# ------------------------------------------------------------------
# Source mappings
# URL templates use Python .format() with keys:
#   {state_slug}, {game_slug}, {year}, {month} (zero-padded)
# ------------------------------------------------------------------
SOURCE_MAPPINGS: list[SourceJobMapping] = [
    # ---- lottery.net (priority 1) ----
    #
    # lottery.net organises results by draw-time-specific game slug on yearly pages.
    # URL pattern:  https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}
    #
    # Each slug maps to one draw time — no splitting required in the parser.
    # The {month} placeholder in build_url() is passed but unused in these templates
    # because lottery.net pages cover a full year; the parser caches the year page
    # and slices results to the requested month.
    #
    # Slug reference (verified against live site):
    #   cash-3-midday   cash-3-evening   cash-3-night
    #   cash-4-midday   cash-4-evening   cash-4-night
    #
    SourceJobMapping(
        job_def=_GA_PICK3_MIDDAY,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],  # verified
        source_state_slug="georgia",
        source_game_slug="cash-3-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=True,
    ),
    SourceJobMapping(
        job_def=_GA_PICK3_EVENING,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],  # verified
        source_state_slug="georgia",
        source_game_slug="cash-3-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=True,
    ),
    SourceJobMapping(
        job_def=_GA_PICK3_NIGHT,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],  # verified
        source_state_slug="georgia",
        source_game_slug="cash-3-night",
        source_draw_time_label="Night",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2012, slug_verified=True,
    ),
    SourceJobMapping(
        job_def=_GA_PICK4_MIDDAY,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],  # verified
        source_state_slug="georgia",
        source_game_slug="cash-4-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=True,
    ),
    SourceJobMapping(
        job_def=_GA_PICK4_EVENING,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],  # verified
        source_state_slug="georgia",
        source_game_slug="cash-4-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=True,
    ),
    SourceJobMapping(
        job_def=_GA_PICK4_NIGHT,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],  # verified
        source_state_slug="georgia",
        source_game_slug="cash-4-night",
        source_draw_time_label="Night",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2012, slug_verified=True,
    ),

    # ---- lotterycorner.com (priority 2) ----
    SourceJobMapping(
        job_def=_GA_PICK3_MIDDAY,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="georgia",
        source_game_slug="cash-3",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/georgia/cash-3/{year}-{month:02d}.html",
        source_min_year=2005,
    ),
    SourceJobMapping(
        job_def=_GA_PICK3_EVENING,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="georgia",
        source_game_slug="cash-3",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/georgia/cash-3/{year}-{month:02d}.html",
        source_min_year=2005,
    ),
    SourceJobMapping(
        job_def=_GA_PICK3_NIGHT,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="georgia",
        source_game_slug="cash-3",
        source_draw_time_label="Night",
        url_template="https://www.lotterycorner.com/georgia/cash-3/{year}-{month:02d}.html",
        source_min_year=2012,
    ),
    SourceJobMapping(
        job_def=_GA_PICK4_MIDDAY,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="georgia",
        source_game_slug="cash-4",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/georgia/cash-4/{year}-{month:02d}.html",
        source_min_year=2005,
    ),
    SourceJobMapping(
        job_def=_GA_PICK4_EVENING,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="georgia",
        source_game_slug="cash-4",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/georgia/cash-4/{year}-{month:02d}.html",
        source_min_year=2005,
    ),
    SourceJobMapping(
        job_def=_GA_PICK4_NIGHT,
        source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="georgia",
        source_game_slug="cash-4",
        source_draw_time_label="Night",
        url_template="https://www.lotterycorner.com/georgia/cash-4/{year}-{month:02d}.html",
        source_min_year=2012,
    ),

    # lotteryusa.com is intentionally excluded for GA.
    # GA runs 3 draws/day (midday, evening, night) but lotteryusa.com serves a
    # single unlabeled daily aggregate — no draw_time label appears on the page.
    # Mapping it to specific draw_time slots would duplicate the same result
    # across all three slots, corrupting backtest hit counts.
    # Fallback for GA is lotterycorner.com (priority 2, per-draw-time pages).
]
