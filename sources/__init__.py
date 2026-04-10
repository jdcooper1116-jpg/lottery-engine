"""
lottery_engine/sources/__init__.py
Parser registry. Maps source_name -> parser instance.
"""
from registry.enums import SourceName
from sources.lottery_net import LotteryNetParser
from sources.lotterycorner import LotteryCornerParser
from sources.lotteryusa import LotteryUSAParser
from sources.base import SourceParser, RawDrawResult, normalize_number, compute_sorted_digits

_PARSERS: dict[str, SourceParser] = {
    SourceName.LOTTERY_NET:   LotteryNetParser(),
    SourceName.LOTTERYCORNER: LotteryCornerParser(),
    SourceName.LOTTERYUSA:    LotteryUSAParser(),
}


def get_parser(source_name: str) -> SourceParser | None:
    return _PARSERS.get(source_name)


def get_all_parsers() -> list[SourceParser]:
    return list(_PARSERS.values())


__all__ = [
    "get_parser", "get_all_parsers",
    "RawDrawResult", "normalize_number", "compute_sorted_digits",
]
