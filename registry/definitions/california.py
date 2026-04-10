"""
lottery_engine/registry/definitions/california.py
California Lottery — stub for Wave 1.
Status: STUB — all slugs ESTIMATED. Verify with dry-run before ingesting.
Notes: CA has 3 draws/day (Morning, Midday, Evening). Morning added ~2004.
"""
from datetime import date
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "CA",
    "state_name":     "California",
    "wave":           1,
    "tier":           "1B",
    "complexity":     "moderate",
    "status":         "stub",
    "games":          ['pick3', 'pick4'],
    "draws_per_day":  3,
    "draw_times":     {'pick3': ['midday', 'evening'], 'pick4': ['evening']},
    "game_names":     {'pick3': 'Daily 3', 'pick4': 'Daily 4'},
    "slugs_verified": False,
    "notes":          'CA Daily 3 uses Midday and Evening on lottery.net. CA Daily 4 uses Evening on lottery.net.' ,
}

_CA_PICK3_MORNING = DrawJobDef(
    state="CA", game_type="pick3", draw_time="midday",
    draw_label="California Daily 3 Midday", schedule_version="v1",
    active_start_date=None,  # extra draw time — verify exact start date
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="DISABLED",
    is_active=False,
)
_CA_PICK3_MIDDAY = DrawJobDef(
    state="CA", game_type="pick3", draw_time="midday",
    draw_label="California Daily 3 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_CA_PICK3_EVENING = DrawJobDef(
    state="CA", game_type="pick3", draw_time="evening",
    draw_label="California Daily 3 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)
_CA_PICK4_MORNING = DrawJobDef(
    state="CA", game_type="pick4", draw_time="midday",
    draw_label="California Daily 4 Morning", schedule_version="v1",
    active_start_date=None,  # disabled; lottery.net does not support CA Daily 4 Morning
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_CA_PICK4_MIDDAY = DrawJobDef(
    state="CA", game_type="pick4", draw_time="midday",
    draw_label="California Daily 4 Midday", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="midday",
    notes="STUB",
)
_CA_PICK4_EVENING = DrawJobDef(
    state="CA", game_type="pick4", draw_time="evening",
    draw_label="California Daily 4 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)

JOB_DEFINITIONS: list[DrawJobDef] = [
    _CA_PICK3_MORNING,
    _CA_PICK3_MIDDAY,
    _CA_PICK3_EVENING,
    _CA_PICK4_MORNING,
    _CA_PICK4_MIDDAY,
    _CA_PICK4_EVENING,
]

SOURCE_MAPPINGS: list[SourceJobMapping] = [
    SourceJobMapping(
        job_def=_CA_PICK3_MORNING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="california", source_game_slug="daily-3-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /california/daily-3-midday/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_CA_PICK3_MORNING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="california", source_game_slug="daily-3",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_CA_PICK3_MORNING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="california", source_game_slug="daily-3",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_CA_PICK3_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="california", source_game_slug="daily-3-midday",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /california/daily-3-midday/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_CA_PICK3_MIDDAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="california", source_game_slug="daily-3",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_CA_PICK3_MIDDAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="california", source_game_slug="daily-3",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_CA_PICK3_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="california", source_game_slug="daily-3-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /california/daily-3-evening/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_CA_PICK3_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="california", source_game_slug="daily-3",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_CA_PICK3_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="california", source_game_slug="daily-3",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_CA_PICK4_MORNING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="california", source_game_slug="daily-4-morning",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="DISABLED: lottery.net does not use /california/daily-4-morning/numbers/2024",
        is_enabled=False,
    ),
    SourceJobMapping(
        job_def=_CA_PICK4_MORNING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="california", source_game_slug="daily-4",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_CA_PICK4_MORNING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="california", source_game_slug="daily-4",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_CA_PICK4_MIDDAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="california", source_game_slug="daily-4",
        source_draw_time_label="Midday",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /california/daily-4/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_CA_PICK4_MIDDAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="california", source_game_slug="daily-4",
        source_draw_time_label="Midday",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_CA_PICK4_MIDDAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="california", source_game_slug="daily-4",
        source_draw_time_label="Midday",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_CA_PICK4_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="california", source_game_slug="daily-4",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /california/daily-4/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_CA_PICK4_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="california", source_game_slug="daily-4",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_CA_PICK4_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="california", source_game_slug="daily-4",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
]
