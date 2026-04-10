"""
lottery_engine/registry/definitions/texas.py
Texas Lottery — stub for Wave 1.
Status: STUB — all slugs ESTIMATED. Verify with dry-run before ingesting.
Notes: HIGH COMPLEXITY: 4 draws/day (Morning, Day, Evening, Night). Pick 4 called 'Daily 4'. Validate schedule history; draw count changed over time.
"""
from datetime import date
from ..models import DrawJobDef, SourceJobMapping
from ..enums import SourceName, SOURCE_PRIORITIES

REGISTRY_META = {
    "state_code":     "TX",
    "state_name":     "Texas",
    "wave":           1,
    "tier":           "1C",
    "complexity":     "high",
    "status":         "stub",
    "games":          ['pick3', 'pick4'],
    "draws_per_day":  4,
    "draw_times":     {'pick3': ['morning', 'day', 'evening', 'night'], 'pick4': ['morning', 'day', 'evening', 'night']},
    "game_names":     {'pick3': 'Pick 3', 'pick4': 'Daily 4'},
    "slugs_verified": False,
    "notes":          "HIGH COMPLEXITY: 4 draws/day (Morning, Day, Evening, Night). Pick 4 called 'Daily 4'. Validate schedule history; draw count changed over time.",
}

_TX_PICK3_MORNING = DrawJobDef(
    state="TX", game_type="pick3", draw_time="morning",
    draw_label="Texas Pick 3 Morning", schedule_version="v1",
    active_start_date=None,  # extra draw time — verify exact start date
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="morning",
    notes="STUB",
)
_TX_PICK3_DAY = DrawJobDef(
    state="TX", game_type="pick3", draw_time="day",
    draw_label="Texas Pick 3 Day", schedule_version="v1",
    active_start_date=None,  # extra draw time — verify exact start date
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="day",
    notes="STUB",
)
_TX_PICK3_EVENING = DrawJobDef(
    state="TX", game_type="pick3", draw_time="evening",
    draw_label="Texas Pick 3 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)
_TX_PICK3_NIGHT = DrawJobDef(
    state="TX", game_type="pick3", draw_time="night",
    draw_label="Texas Pick 3 Night", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="night",
    notes="STUB",
)
_TX_PICK4_MORNING = DrawJobDef(
    state="TX", game_type="pick4", draw_time="morning",
    draw_label="Texas Daily 4 Morning", schedule_version="v1",
    active_start_date=None,  # extra draw time — verify exact start date
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="morning",
    notes="STUB",
)
_TX_PICK4_DAY = DrawJobDef(
    state="TX", game_type="pick4", draw_time="day",
    draw_label="Texas Daily 4 Day", schedule_version="v1",
    active_start_date=None,  # extra draw time — verify exact start date
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="day",
    notes="STUB",
)
_TX_PICK4_EVENING = DrawJobDef(
    state="TX", game_type="pick4", draw_time="evening",
    draw_label="Texas Daily 4 Evening", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="evening",
    notes="STUB",
)
_TX_PICK4_NIGHT = DrawJobDef(
    state="TX", game_type="pick4", draw_time="night",
    draw_label="Texas Daily 4 Night", schedule_version="v1",
    active_start_date=None, active_end_date=None,
    source_min_year=2002, source_max_year=None,
    draw_days="daily", canonical_time_key="night",
    notes="STUB",
)

JOB_DEFINITIONS: list[DrawJobDef] = [
    _TX_PICK3_MORNING,
    _TX_PICK3_DAY,
    _TX_PICK3_EVENING,
    _TX_PICK3_NIGHT,
    _TX_PICK4_MORNING,
    _TX_PICK4_DAY,
    _TX_PICK4_EVENING,
    _TX_PICK4_NIGHT,
]

SOURCE_MAPPINGS: list[SourceJobMapping] = [
    SourceJobMapping(
        job_def=_TX_PICK3_MORNING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="texas", source_game_slug="pick-3-morning",
        source_draw_time_label="Morning",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /texas/pick-3-morning/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_MORNING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="texas", source_game_slug="pick-3",
        source_draw_time_label="Morning",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_MORNING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="texas", source_game_slug="pick-3",
        source_draw_time_label="Morning",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_DAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="texas", source_game_slug="pick-3-day",
        source_draw_time_label="Day",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /texas/pick-3-day/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_DAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="texas", source_game_slug="pick-3",
        source_draw_time_label="Day",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_DAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="texas", source_game_slug="pick-3",
        source_draw_time_label="Day",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="texas", source_game_slug="pick-3-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /texas/pick-3-evening/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="texas", source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="texas", source_game_slug="pick-3",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_NIGHT, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="texas", source_game_slug="pick-3-night",
        source_draw_time_label="Night",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /texas/pick-3-night/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_NIGHT, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="texas", source_game_slug="pick-3",
        source_draw_time_label="Night",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_TX_PICK3_NIGHT, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="texas", source_game_slug="pick-3",
        source_draw_time_label="Night",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_MORNING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="texas", source_game_slug="daily-4-morning",
        source_draw_time_label="Morning",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /texas/daily-4-morning/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_MORNING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="texas", source_game_slug="daily-4",
        source_draw_time_label="Morning",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_MORNING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="texas", source_game_slug="daily-4",
        source_draw_time_label="Morning",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_DAY, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="texas", source_game_slug="daily-4-day",
        source_draw_time_label="Day",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /texas/daily-4-day/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_DAY, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="texas", source_game_slug="daily-4",
        source_draw_time_label="Day",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_DAY, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="texas", source_game_slug="daily-4",
        source_draw_time_label="Day",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_EVENING, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="texas", source_game_slug="daily-4-evening",
        source_draw_time_label="Evening",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /texas/daily-4-evening/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_EVENING, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="texas", source_game_slug="daily-4",
        source_draw_time_label="Evening",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_EVENING, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="texas", source_game_slug="daily-4",
        source_draw_time_label="Evening",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_NIGHT, source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_state_slug="texas", source_game_slug="daily-4-night",
        source_draw_time_label="Night",
        url_template="https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}",
        source_min_year=2002, slug_verified=False,
        notes="ESTIMATED: verify /texas/daily-4-night/numbers/2024",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_NIGHT, source_name=SourceName.LOTTERYCORNER,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYCORNER],
        source_state_slug="texas", source_game_slug="daily-4",
        source_draw_time_label="Night",
        url_template="https://www.lotterycorner.com/{state_slug}/{game_slug}/{year}-{month:02d}.html",
        source_min_year=2005, slug_verified=False,
        notes="ESTIMATED",
    ),
    SourceJobMapping(
        job_def=_TX_PICK4_NIGHT, source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_state_slug="texas", source_game_slug="daily-4",
        source_draw_time_label="Night",
        url_template="https://lotteryusa.com/{state_slug}/{game_slug}/",
        source_min_year=2018, slug_verified=False,
        notes="ESTIMATED. Recent only.",
    ),
]
