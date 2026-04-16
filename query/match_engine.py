"""
lottery_engine/query/match_engine.py

Pluggable match engine for draw result matching.
v1 ships EXACT only. All other modes are registered as implemented.
No code outside this file needs to change when a new match mode is added.

Match functions signature: (candidate: str, winning: str) -> bool
Both inputs are plain-digit strings with leading zeros preserved.
"""
from __future__ import annotations
from typing import Callable

from registry.enums import DrawTime

# ------------------------------------------------------------------
# Match mode constants (mirrors MatchMode values in query/models)
# ------------------------------------------------------------------
EXACT    = "exact"
STRAIGHT = "straight"   # alias for exact — same match, clearer name for dream apps
BOX      = "box"
DIGIT    = "digit"
PAIR     = "pair"
TRIPLE   = "triple"
PRESENCE = "presence"


# ------------------------------------------------------------------
# v1 implementations
# ------------------------------------------------------------------

def _exact(candidate: str, winning: str) -> bool:
    """Straight/exact match. '123' matches '123' only."""
    return candidate == winning


def _box(candidate: str, winning: str) -> bool:
    """
    Box match: any permutation of the candidate's digits.
    '123' box-matches '321', '213', '132', etc.
    """
    return len(candidate) == len(winning) and sorted(candidate) == sorted(winning)


def _digit_presence(candidate: str, winning: str) -> bool:
    """
    Presence match: every digit in candidate appears in winning
    at least as many times.

    Leading-zero semantics:
    multi-character candidates that start with "0" use ordered
    substring matching instead of unordered digit presence.
    Example: "03" matches "034" but does NOT match "340".
    """
    candidate = str(candidate)
    winning = str(winning)

    if len(candidate) > 1 and candidate.startswith("0"):
        return candidate in winning

    from collections import Counter
    c_count = Counter(candidate)
    w_count = Counter(winning)
    return all(w_count[d] >= n for d, n in c_count.items())


def _pair(candidate: str, winning: str) -> bool:
    """
    Pair match: any consecutive 2-digit pair from candidate
    appears as a substring in winning.
    '123' pairs are '12','23'. Matches winning if either is present.
    """
    if len(candidate) < 2:
        return False
    pairs_in_candidate = {candidate[i:i+2] for i in range(len(candidate) - 1)}
    pairs_in_winning   = {winning[i:i+2]   for i in range(len(winning)   - 1)}
    return bool(pairs_in_candidate & pairs_in_winning)


def _triple(candidate: str, winning: str) -> bool:
    """
    Triple match: any consecutive 3-digit run from candidate
    appears as a substring in winning.
    """
    if len(candidate) < 3:
        return False
    triples_in_candidate = {candidate[i:i+3] for i in range(len(candidate) - 2)}
    triples_in_winning   = {winning[i:i+3]   for i in range(len(winning)   - 2)}
    return bool(triples_in_candidate & triples_in_winning)


# ------------------------------------------------------------------
# Registry — map mode string -> function
# ------------------------------------------------------------------
_MATCH_ENGINES: dict[str, Callable[[str, str], bool]] = {
    EXACT:    _exact,
    STRAIGHT: _exact,     # alias — "straight" is the lottery world's term for exact-order match
    BOX:      _box,
    DIGIT:    _digit_presence,
    PAIR:     _pair,
    TRIPLE:   _triple,
    PRESENCE: _digit_presence,  # alias
}


def apply_match(candidate: str, winning: str, mode: str = EXACT) -> bool:
    """
    Apply a match mode. Raises ValueError for unregistered modes.
    Both inputs must be plain digit strings.
    """
    fn = _MATCH_ENGINES.get(mode)
    if fn is None:
        raise ValueError(
            f"Match mode {mode!r} is not registered. "
            f"Available: {list(_MATCH_ENGINES.keys())}"
        )
    return fn(candidate, winning)


def filter_draws_by_candidates(
    draws: list,           # list of DrawRecord
    candidates: list[str],
    mode: str = EXACT,
) -> list[tuple]:
    """
    Filter a list of DrawRecords against a list of candidate numbers.
    Returns list of (candidate, draw_record) tuples for each match.
    """
    hits = []
    for draw in draws:
        for candidate in candidates:
            if apply_match(candidate, draw.winning_number, mode):
                hits.append((candidate, draw))
    return hits


def register_match_engine(mode: str, fn: Callable[[str, str], bool]) -> None:
    """Register a custom match engine at runtime."""
    _MATCH_ENGINES[mode] = fn


def available_modes() -> list[str]:
    return list(_MATCH_ENGINES.keys())