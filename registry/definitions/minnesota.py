"""
lottery_engine/registry/definitions/minnesota.py
Minnesota Lottery — special-case stub for Wave 2.
Status: STUB — slugs ESTIMATED. Verify with dry-run before ingesting.
Notes: Minnesota currently appears to have Pick 3 only on lottery.net (formerly Daily 3), single evening draw.
Pick 4 is intentionally omitted pending confirmation.
"""
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "MN",
    "state_name":     "Minnesota",
    "wave":           2,
    "tier":           "special",
    "complexity":     "high",
    "status":         "stub",
    "games":          ['pick3'],
    "draws_per_day":  1,
    "draw_times":     {'pick3': ['evening']},
    "game_names":     {'pick3': 'Pick 3'},
    "slugs_verified": False,
    "notes":          "Special-case: Pick 3 only for now; no Pick 4 scaffold until coverage is confirmed.",
}

_MN_PICK3_EVENING = DrawJobDef(
    state="MN", game_type="pick3", draw_time="evening",
    draw_label="Minnesota Pick 3 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)

JOB_DEFINITIONS = [_MN_PICK3_EVENING]

SOURCE_MAPPINGS = [
    SourceJobMapping(
        job_def=_MN_PICK3_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="minnesota", source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /minnesota/pick-3/numbers/2024",
    ),
]
