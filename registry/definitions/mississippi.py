"""
lottery_engine/registry/definitions/mississippi.py
Mississippi Lottery — special-case stub for Wave 2.
Status: STUB — slugs ESTIMATED. Verify with dry-run before ingesting.
Notes: Mississippi uses Cash 3 / Cash 4 naming, midday + evening.
"""
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "MS",
    "state_name":     "Mississippi",
    "wave":           2,
    "tier":           "special",
    "complexity":     "moderate",
    "status":         "stub",
    "games":          ['pick3', 'pick4'],
    "draws_per_day":  2,
    "draw_times":     {'pick3': ['midday', 'evening'], 'pick4': ['midday', 'evening']},
    "game_names":     {'pick3': 'Cash 3', 'pick4': 'Cash 4'},
    "slugs_verified": False,
    "notes":          "Special-case: cash-3/cash-4 slugs rather than pick-3/pick-4.",
}

_MS_PICK3_MIDDAY = DrawJobDef(
    state="MS", game_type="pick3", draw_time="midday",
    draw_label="Mississippi Cash 3 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2019, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_MS_PICK3_EVENING = DrawJobDef(
    state="MS", game_type="pick3", draw_time="evening",
    draw_label="Mississippi Cash 3 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2019, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)
_MS_PICK4_MIDDAY = DrawJobDef(
    state="MS", game_type="pick4", draw_time="midday",
    draw_label="Mississippi Cash 4 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2019, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_MS_PICK4_EVENING = DrawJobDef(
    state="MS", game_type="pick4", draw_time="evening",
    draw_label="Mississippi Cash 4 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2019, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)

JOB_DEFINITIONS = [
    _MS_PICK3_MIDDAY, _MS_PICK3_EVENING, _MS_PICK4_MIDDAY, _MS_PICK4_EVENING,
]

SOURCE_MAPPINGS = [
    SourceJobMapping(
        job_def=_MS_PICK3_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="mississippi", source_game_slug="cash-3-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2019, slug_verified=False,
        notes="ESTIMATED: verify /mississippi/cash-3-midday/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_MS_PICK3_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="mississippi", source_game_slug="cash-3-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2019, slug_verified=False,
        notes="ESTIMATED: verify /mississippi/cash-3-evening/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_MS_PICK4_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="mississippi", source_game_slug="cash-4-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2019, slug_verified=False,
        notes="ESTIMATED: verify /mississippi/cash-4-midday/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_MS_PICK4_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="mississippi", source_game_slug="cash-4-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2019, slug_verified=False,
        notes="ESTIMATED: verify /mississippi/cash-4-evening/numbers/2024",
    ),
]
