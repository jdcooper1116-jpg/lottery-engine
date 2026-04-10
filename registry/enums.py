"""
lottery_engine/registry/enums.py
Canonical enum values used across the entire engine.
These string values are what gets stored in the database.
Do not change values once data is in production.
"""
from enum import Enum


class DrawTime(str, Enum):
    """Canonical draw time slots. One and only one set of values."""
    MORNING = "morning"   # early AM, typically 9-11 AM
    DAY     = "day"       # daytime with no midday alignment
    MIDDAY  = "midday"    # noon-aligned, 11 AM - 1 PM range
    EVENING = "evening"   # early evening, 5-8 PM range
    NIGHT   = "night"     # late draw, 8 PM - midnight range
    UNKNOWN = "unknown"   # normalization failed; treat as data quality flag

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]


class GameType(str, Enum):
    PICK3 = "pick3"
    PICK4 = "pick4"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]


class SourceName(str, Enum):
    LOTTERY_NET   = "lottery.net"
    LOTTERYCORNER = "lotterycorner.com"
    LOTTERYUSA    = "lotteryusa.com"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]


class CoverageStatus(str, Enum):
    NOT_SCRAPED        = "not_scraped"
    NO_DRAW_SCHEDULED  = "no_draw_scheduled"
    ACCEPTED           = "accepted"
    CONFLICT           = "conflict"
    ANOMALY            = "anomaly"
    SCRAPE_ERROR       = "scrape_error"


class ReconciliationStatus(str, Enum):
    PENDING   = "pending"
    ACCEPTED  = "accepted"
    DUPLICATE = "duplicate"
    CONFLICT  = "conflict"
    ANOMALY   = "anomaly"


# Source priority map. Lower number = higher authority.
SOURCE_PRIORITIES: dict[str, int] = {
    SourceName.LOTTERY_NET:   1,
    SourceName.LOTTERYCORNER: 2,
    SourceName.LOTTERYUSA:    3,
}
