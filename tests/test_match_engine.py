"""
lottery_engine/tests/test_match_engine.py
"""
import pytest
from query.match_engine import apply_match, filter_draws_by_candidates, available_modes
from query.match_engine import EXACT, BOX, DIGIT, PAIR, TRIPLE, PRESENCE


class TestExactMatch:
    def test_exact_match(self):
        assert apply_match("123", "123", EXACT) is True

    def test_exact_no_match(self):
        assert apply_match("123", "124", EXACT) is False

    def test_leading_zeros_exact(self):
        assert apply_match("034", "034", EXACT) is True
        assert apply_match("034", "340", EXACT) is False
        assert apply_match("034", "34", EXACT) is False

    def test_pick4_exact(self):
        assert apply_match("1234", "1234", EXACT) is True
        assert apply_match("1234", "4321", EXACT) is False

    def test_exact_is_default(self):
        assert apply_match("123", "123") is True


class TestBoxMatch:
    def test_same_digits_different_order(self):
        assert apply_match("123", "321", BOX) is True
        assert apply_match("123", "213", BOX) is True
        assert apply_match("123", "132", BOX) is True

    def test_exact_is_also_box(self):
        assert apply_match("123", "123", BOX) is True

    def test_different_digits(self):
        assert apply_match("123", "124", BOX) is False

    def test_leading_zeros_box(self):
        assert apply_match("034", "340", BOX) is True
        assert apply_match("034", "403", BOX) is True
        assert apply_match("034", "403", BOX) is True

    def test_different_lengths_no_match(self):
        assert apply_match("123", "1234", BOX) is False

    def test_repeated_digits(self):
        assert apply_match("112", "211", BOX) is True
        assert apply_match("112", "121", BOX) is True
        assert apply_match("112", "122", BOX) is False


class TestDigitPresenceMatch:
    def test_all_digits_present(self):
        assert apply_match("12", "123", DIGIT) is True

    def test_digit_not_present(self):
        assert apply_match("19", "123", DIGIT) is False

    def test_exact_satisfies_presence(self):
        assert apply_match("123", "123", DIGIT) is True

    def test_leading_zero_presence(self):
        assert apply_match("03", "034", DIGIT) is True
        assert apply_match("03", "340", DIGIT) is False  # 0 not in 340


class TestPairMatch:
    def test_pair_present(self):
        assert apply_match("123", "512", PAIR) is True  # "12" in "512"
        assert apply_match("123", "423", PAIR) is True  # "23" in "423"

    def test_no_pair_match(self):
        assert apply_match("123", "456", PAIR) is False

    def test_exact_has_pair(self):
        assert apply_match("123", "123", PAIR) is True

    def test_too_short_candidate(self):
        assert apply_match("1", "123", PAIR) is False


class TestTripleMatch:
    def test_triple_present(self):
        assert apply_match("1234", "5123", TRIPLE) is True   # "123" in "5123"
        assert apply_match("1234", "2345", TRIPLE) is True   # "234" in "2345"

    def test_no_triple(self):
        assert apply_match("1234", "5678", TRIPLE) is False

    def test_too_short_candidate(self):
        assert apply_match("12", "1234", TRIPLE) is False


class TestUnregisteredMode:
    def test_raises_value_error(self):
        with pytest.raises(ValueError, match="not registered"):
            apply_match("123", "123", "superbox")


class TestFilterDrawsByCandidate:
    def test_returns_matching_pairs(self, sample_draws):
        """Integration test using sample_draws fixture."""
        from query.service import _fetch_draws
        from query.models import QueryFilters
        from db.connection import get_connection
        import os

        # Patch DB path to use the seeded fixture connection
        # We'll query directly
        from datetime import date as d

        # Use the fixture's conn
        conn = sample_draws

        # Manually fetch draws
        rows = conn.execute(
            "SELECT * FROM draws WHERE state='GA' AND game_type='pick3'"
        ).fetchall()

        from query.models import DrawRecord
        draws = [DrawRecord.from_row(r) for r in rows]

        # Test exact match
        hits = filter_draws_by_candidates(draws, ["123"], EXACT)
        assert len(hits) == 1
        cand, draw = hits[0]
        assert cand == "123"
        assert draw.winning_number == "123"

    def test_no_hits_returns_empty(self, sample_draws):
        rows = sample_draws.execute(
            "SELECT * FROM draws WHERE state='GA' AND game_type='pick3'"
        ).fetchall()
        from query.models import DrawRecord
        draws = [DrawRecord.from_row(r) for r in rows]
        hits = filter_draws_by_candidates(draws, ["999"], EXACT)
        assert hits == []

    def test_multiple_candidates(self, sample_draws):
        rows = sample_draws.execute(
            "SELECT * FROM draws WHERE state='GA' AND game_type='pick3'"
        ).fetchall()
        from query.models import DrawRecord
        draws = [DrawRecord.from_row(r) for r in rows]
        hits = filter_draws_by_candidates(draws, ["123", "456"], EXACT)
        hit_numbers = {draw.winning_number for _, draw in hits}
        assert "123" in hit_numbers
        assert "456" in hit_numbers

    def test_leading_zero_candidate(self, sample_draws):
        rows = sample_draws.execute(
            "SELECT * FROM draws WHERE state='GA' AND game_type='pick3'"
        ).fetchall()
        from query.models import DrawRecord
        draws = [DrawRecord.from_row(r) for r in rows]
        # "034" is in sample_draws
        hits = filter_draws_by_candidates(draws, ["034"], EXACT)
        assert len(hits) == 1
        assert hits[0][1].winning_number == "034"


class TestAvailableModes:
    def test_exact_in_modes(self):
        assert EXACT in available_modes()

    def test_box_in_modes(self):
        assert BOX in available_modes()
