"""
lottery_engine/registry/definitions/oregon.py
Oregon Lottery — special-case stub for Wave 2.
Status: STUB — slugs ESTIMATED. Verify with dry-run before ingesting.
Notes: Oregon appears to offer Pick 4 only on lottery.net, with four daily draw times.
Mapped to canonical internal draw_time buckets:
1PM -> midday, 4PM -> day, 7PM -> evening, 10PM -> night.
"""
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "OR",
    "state_name":     "Oregon",
    "wave":           2,
    "tier":           "special",
    "complexity":     "high",
    "status":         "stub",
    "games":          ['pick4'],
    "draws_per_day":  4,
    "draw_times":     {'pick4': ['midday', 'day', 'evening', 'night']},
    "game_names":     {'pick4': 'Pick 4'},
    "slugs_verified": False,
    "notes":          "Special-case: Oregon Pick 4 only. 1PM->midday, 4PM->day, 7PM->evening, 10PM->night.",
}

_OR_PICK4_1PM = DrawJobDef(
    state="OR", game_type="pick4", draw_time="midday",
    draw_label="Oregon Pick 4 1PM", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_OR_PICK4_4PM = DrawJobDef(
    state="OR", game_type="pick4", draw_time="day",
    draw_label="Oregon Pick 4 4PM", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="day",
    notes="STUB",
)
_OR_PICK4_7PM = DrawJobDef(
    state="OR", game_type="pick4", draw_time="evening",
    draw_label="Oregon Pick 4 7PM", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)
_OR_PICK4_10PM = DrawJobDef(
    state="OR", game_type="pick4", draw_time="night",
    draw_label="Oregon Pick 4 10PM", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="night",
    notes="STUB",
)

JOB_DEFINITIONS = [
    _OR_PICK4_1PM,
    _OR_PICK4_4PM,
    _OR_PICK4_7PM,
    _OR_PICK4_10PM,
]

SOURCE_MAPPINGS = [
    SourceJobMapping(
        job_def=_OR_PICK4_1PM, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="oregon", source_game_slug="pick-4-1pm",
        source_draw_time_label="1PM",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /oregon/pick-4-1pm/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_OR_PICK4_4PM, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="oregon", source_game_slug="pick-4-4pm",
        source_draw_time_label="4PM",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /oregon/pick-4-4pm/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_OR_PICK4_7PM, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="oregon", source_game_slug="pick-4-7pm",
        source_draw_time_label="7PM",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /oregon/pick-4-7pm/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_OR_PICK4_10PM, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="oregon", source_game_slug="pick-4-10pm",
        source_draw_time_label="10PM",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /oregon/pick-4-10pm/numbers/2024",
    ),
]
