"""
lottery_engine/registry/definitions/washington.py
Washington Lottery — special-case stub for Wave 2.
Status: STUB — slugs ESTIMATED. Verify with dry-run before ingesting.
Notes: Washington uses Pick 3 and Match 4. Match 4 is modeled here as the engine's pick4-equivalent.
"""
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "WA",
    "state_name":     "Washington",
    "wave":           2,
    "tier":           "special",
    "complexity":     "high",
    "status":         "stub",
    "games":          ['pick3', 'pick4'],
    "draws_per_day":  1,
    "draw_times":     {'pick3': ['evening'], 'pick4': ['evening']},
    "game_names":     {'pick3': 'Pick 3', 'pick4': 'Match 4'},
    "slugs_verified": False,
    "notes":          "Special-case: Washington uses Pick 3 and Match 4; Match 4 is the pick4-equivalent.",
}

_WA_PICK3_EVENING = DrawJobDef(
    state="WA", game_type="pick3", draw_time="evening",
    draw_label="Washington Pick 3", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)

_WA_PICK4_EVENING = DrawJobDef(
    state="WA", game_type="pick4", draw_time="evening",
    draw_label="Washington Match 4", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)

JOB_DEFINITIONS = [
    _WA_PICK3_EVENING,
    _WA_PICK4_EVENING,
]

SOURCE_MAPPINGS = [
    SourceJobMapping(
        job_def=_WA_PICK3_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="washington", source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /washington/pick-3/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_WA_PICK4_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="washington", source_game_slug="match-4",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /washington/match-4/numbers/2024",
    ),
]
