"""
lottery_engine/registry/definitions/ohio.py
Ohio Lottery — stub for Wave 1.
Status: STUB — all slugs ESTIMATED. Verify with dry-run before ingesting.
Notes: Standard 2-draw state. Standard game names.
"""
from datetime import date
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "OH",
    "state_name":     "Ohio",
    "wave":           1,
    "tier":           "1B",
    "complexity":     "standard",
    "status":         "stub",
    "games":          ['pick3', 'pick4'],
    "draws_per_day":  2,
    "draw_times":     {'pick3': ['midday', 'evening'], 'pick4': ['midday', 'evening']},
    "game_names":     {'pick3': 'Pick 3', 'pick4': 'Pick 4'},
    "slugs_verified": False,
    "notes":          'Standard 2-draw state. Standard game names.',
}

_OH_PICK3_MIDDAY = DrawJobDef(
    state="OH", game_type="pick3", draw_time="midday",
    draw_label="Ohio Pick 3 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_OH_PICK3_EVENING = DrawJobDef(
    state="OH", game_type="pick3", draw_time="evening",
    draw_label="Ohio Pick 3 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)
_OH_PICK4_MIDDAY = DrawJobDef(
    state="OH", game_type="pick4", draw_time="midday",
    draw_label="Ohio Pick 4 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_OH_PICK4_EVENING = DrawJobDef(
    state="OH", game_type="pick4", draw_time="evening",
    draw_label="Ohio Pick 4 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)

JOB_DEFINITIONS: list[DrawJobDef] = [
    _OH_PICK3_MIDDAY,
    _OH_PICK3_EVENING,
    _OH_PICK4_MIDDAY,
    _OH_PICK4_EVENING,
]

SOURCE_MAPPINGS: list[SourceJobMapping] = [
    SourceJobMapping(
        job_def=_OH_PICK3_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="ohio", source_game_slug="pick-3-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /ohio/pick-3-midday/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_OH_PICK3_MIDDAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="ohio", source_game_slug="pick-3",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_OH_PICK3_MIDDAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="ohio", source_game_slug="pick-3",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_OH_PICK3_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="ohio", source_game_slug="pick-3-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /ohio/pick-3-evening/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_OH_PICK3_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="ohio", source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_OH_PICK3_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="ohio", source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_OH_PICK4_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="ohio", source_game_slug="pick-4-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /ohio/pick-4-midday/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_OH_PICK4_MIDDAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="ohio", source_game_slug="pick-4",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_OH_PICK4_MIDDAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="ohio", source_game_slug="pick-4",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_OH_PICK4_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="ohio", source_game_slug="pick-4-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /ohio/pick-4-evening/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_OH_PICK4_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="ohio", source_game_slug="pick-4",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_OH_PICK4_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="ohio", source_game_slug="pick-4",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
]
