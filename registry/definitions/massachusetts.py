"""
lottery_engine/registry/definitions/massachusetts.py
Massachusetts Lottery — special-case stub for Wave 2.
Status: STUB — slugs ESTIMATED. Verify with dry-run before ingesting.
Notes: Massachusetts uses "Numbers" branding with midday and evening pages on lottery.net.
Lottery.net pages appear as /massachusetts/numbers-midday/numbers/{year} and /numbers-evening/numbers/{year}.
"""
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "MA",
    "state_name":     "Massachusetts",
    "wave":           2,
    "tier":           "special",
    "complexity":     "high",
    "status":         "stub",
    "games":          ['pick4'],
    "draws_per_day":  2,
    "draw_times":     {'pick4': ['midday', 'evening']},
    "game_names":     {'pick4': 'Numbers'},
    "slugs_verified": False,
    "notes":          "Special-case: Numbers branding on lottery.net; scaffolded as pick4-equivalent only for now.",
}

_MA_PICK4_MIDDAY = DrawJobDef(
    state="MA", game_type="pick4", draw_time="midday",
    draw_label="Massachusetts Numbers Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_MA_PICK4_EVENING = DrawJobDef(
    state="MA", game_type="pick4", draw_time="evening",
    draw_label="Massachusetts Numbers Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)

JOB_DEFINITIONS = [
    _MA_PICK4_MIDDAY,
    _MA_PICK4_EVENING,
]

SOURCE_MAPPINGS = [
    SourceJobMapping(
        job_def=_MA_PICK4_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="massachusetts", source_game_slug="numbers-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /massachusetts/numbers-midday/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_MA_PICK4_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="massachusetts", source_game_slug="numbers-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /massachusetts/numbers-evening/numbers/2024",
    ),
]
