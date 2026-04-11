"""
lottery_engine/registry/definitions/washington_dc.py
District of Columbia Lottery — special-case stub for Wave 2.
Status: STUB — slugs ESTIMATED. Verify with dry-run before ingesting.
Notes: DC uses DC-3 and DC-4 branding, with midday/evening/night draws.
Lottery.net appears to use /district-of-columbia/.../results/{year}
"""
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "DC",
    "state_name":     "District of Columbia",
    "wave":           2,
    "tier":           "special",
    "complexity":     "high",
    "status":         "stub",
    "games":          ['pick3', 'pick4'],
    "draws_per_day":  3,
    "draw_times":     {'pick3': ['midday', 'evening', 'night'], 'pick4': ['midday', 'evening', 'night']},
    "game_names":     {'pick3': 'DC-3', 'pick4': 'DC-4'},
    "slugs_verified": False,
    "notes":          "Special-case: district-of-columbia slug, dc-3/dc-4 branding, results/{year} pages.",
}

_DC_PICK3_MIDDAY = DrawJobDef(
    state="DC", game_type="pick3", draw_time="midday",
    draw_label="DC-3 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2014, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_DC_PICK3_EVENING = DrawJobDef(
    state="DC", game_type="pick3", draw_time="evening",
    draw_label="DC-3 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2014, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)
_DC_PICK3_NIGHT = DrawJobDef(
    state="DC", game_type="pick3", draw_time="night",
    draw_label="DC-3 Night", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2014, source_max_year=None,
    draw_days="daily", canonical_time_key="night",
    notes="STUB",
)
_DC_PICK4_MIDDAY = DrawJobDef(
    state="DC", game_type="pick4", draw_time="midday",
    draw_label="DC-4 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2014, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_DC_PICK4_EVENING = DrawJobDef(
    state="DC", game_type="pick4", draw_time="evening",
    draw_label="DC-4 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2014, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)
_DC_PICK4_NIGHT = DrawJobDef(
    state="DC", game_type="pick4", draw_time="night",
    draw_label="DC-4 Night", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2014, source_max_year=None,
    draw_days="daily", canonical_time_key="night",
    notes="STUB",
)

JOB_DEFINITIONS = [
    _DC_PICK3_MIDDAY, _DC_PICK3_EVENING, _DC_PICK3_NIGHT,
    _DC_PICK4_MIDDAY, _DC_PICK4_EVENING, _DC_PICK4_NIGHT,
]

SOURCE_MAPPINGS = [
    SourceJobMapping(
        job_def=_DC_PICK3_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="district-of-columbia", source_game_slug="dc-3-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/results/{year}",
        source_min_year=2014, slug_verified=False,
        notes="ESTIMATED: verify /district-of-columbia/dc-3-midday/results/2024",
    ),
    SourceJobMapping(
        job_def=_DC_PICK3_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="district-of-columbia", source_game_slug="dc-3-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/results/{year}",
        source_min_year=2014, slug_verified=False,
        notes="ESTIMATED: verify /district-of-columbia/dc-3-evening/results/2024",
    ),
    SourceJobMapping(
        job_def=_DC_PICK3_NIGHT, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="district-of-columbia", source_game_slug="dc-3-night",
        source_draw_time_label="Night",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/results/{year}",
        source_min_year=2014, slug_verified=False,
        notes="ESTIMATED: verify /district-of-columbia/dc-3-night/results/2024",
    ),
    SourceJobMapping(
        job_def=_DC_PICK4_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="district-of-columbia", source_game_slug="dc-4-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/results/{year}",
        source_min_year=2014, slug_verified=False,
        notes="ESTIMATED: verify /district-of-columbia/dc-4-midday/results/2024",
    ),
    SourceJobMapping(
        job_def=_DC_PICK4_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="district-of-columbia", source_game_slug="dc-4-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/results/{year}",
        source_min_year=2014, slug_verified=False,
        notes="ESTIMATED: verify /district-of-columbia/dc-4-evening/results/2024",
    ),
    SourceJobMapping(
        job_def=_DC_PICK4_NIGHT, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="district-of-columbia", source_game_slug="dc-4-night",
        source_draw_time_label="Night",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/results/{year}",
        source_min_year=2014, slug_verified=False,
        notes="ESTIMATED: verify /district-of-columbia/dc-4-night/results/2024",
    ),
]
