from __future__ import annotations

from typing import Callable

EXACT = "exact"
BOX = "box"
DIGIT = "digit"
PAIR = "pair"
TRIPLE = "triple"
PRESENCE = "presence"


def _exact(candidate: str, winning: str) -> bool:
    return candidate == winning


def _box(candidate: str, winning: str) -> bool:
    return sorted(candidate) == sorted(winning)


def _digit_presence(candidate: str, winning: str) -> bool:
    """
    DIGIT/PRESENCE mode:
    candidate must appear in winning as an ordered contiguous digit sequence.

    Examples:
      "03" in "034" -> True
      "03" in "340" -> False
    """
    return candidate in winning


def _pair(candidate: str, winning: str) -> bool:
    if len(candidate) < 2:
        return False
    pairs_in_candidate = {candidate[i:i+2] for i in range(len(candidate) - 1)}
    pairs_in_winning = {winning[i:i+2] for i in range(len(winning) - 1)}
    return bool(pairs_in_candidate & pairs_in_winning)


def _triple(candidate: str, winning: str) -> bool:
    if len(candidate) < 3:
        return False
    triples_in_candidate = {candidate[i:i+3] for i in range(len(candidate) - 2)}
    triples_in_winning = {winning[i:i+3] for i in range(len(winning) - 2)}
    return bool(triples_in_candidate & triples_in_winning)


_MATCH_ENGINES: dict[str, Callable[[str, str], bool]] = {
    EXACT: _exact,
    BOX: _box,
    DIGIT: _digit_presence,
    PAIR: _pair,
    TRIPLE: _triple,
    PRESENCE: _digit_presence,
}


def apply_match(candidate: str, winning: str, mode: str = EXACT) -> bool:
    fn = _MATCH_ENGINES.get(mode)
    if fn is None:
        raise ValueError(
            f"Match mode {mode!r} is not registered. "
            f"Available: {list(_MATCH_ENGINES.keys())}"
        )
    return fn(candidate, winning)


def filter_draws_by_candidates(
    draws: list,
    candidates: list[str],
    mode: str = EXACT,
) -> list[tuple]:
    hits = []
    for draw in draws:
        for candidate in candidates:
            if apply_match(candidate, draw.winning_number, mode):
                hits.append((candidate, draw))
    return hits


def register_match_engine(mode: str, fn: Callable[[str, str], bool]) -> None:
    _MATCH_ENGINES[mode] = fn


def available_modes() -> list[str]:
    return list(_MATCH_ENGINES.keys())
