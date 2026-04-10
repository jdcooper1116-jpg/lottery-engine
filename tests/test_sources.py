"""
lottery_engine/tests/test_sources.py

Tests for sources/base.py utilities and RawDrawResult construction.
"""
import pytest
from sources.base import normalize_number, compute_sorted_digits, RawDrawResult, date_range_months
from datetime import date


class TestNormalizeNumber:
    def test_plain_number(self):
        assert normalize_number("123") == "123"

    def test_leading_zeros_preserved(self):
        assert normalize_number("034") == "034"
        assert normalize_number("007") == "007"
        assert normalize_number("012") == "012"

    def test_strips_whitespace(self):
        assert normalize_number("  123  ") == "123"

    def test_strips_dashes(self):
        assert normalize_number("1-2-3") == "123"

    def test_strips_spaces_between_digits(self):
        assert normalize_number("1 2 3") == "123"

    def test_empty_string(self):
        assert normalize_number("") == ""

    def test_none_like_input(self):
        assert normalize_number("") == ""

    def test_does_not_cast_to_int(self):
        result = normalize_number("034")
        assert isinstance(result, str)
        assert result[0] == "0"

    def test_four_digit_with_leading_zero(self):
        assert normalize_number("0123") == "0123"


class TestComputeSortedDigits:
    def test_already_sorted(self):
        assert compute_sorted_digits("123") == "123"

    def test_reverse_sorted(self):
        assert compute_sorted_digits("321") == "123"

    def test_with_leading_zero(self):
        assert compute_sorted_digits("034") == "034"
        assert compute_sorted_digits("340") == "034"
        assert compute_sorted_digits("403") == "034"

    def test_repeated_digits(self):
        assert compute_sorted_digits("112") == "112"
        assert compute_sorted_digits("211") == "112"

    def test_all_same(self):
        assert compute_sorted_digits("777") == "777"

    def test_pick4(self):
        assert compute_sorted_digits("4321") == "1234"


class TestRawDrawResult:
    def _make(self, number="123", draw_time="midday"):
        from datetime import datetime, timezone
        return RawDrawResult(
            state="GA",
            game_type="pick3",
            draw_date="2024-03-15",
            draw_time=draw_time,
            winning_number=number,
            source_name="lottery.net",
            source_priority=1,
            source_url="https://example.com",
            raw_draw_time_label="Midday",
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )

    def test_digit_count_auto_set(self):
        r = self._make("123")
        assert r.digit_count == 3

    def test_sorted_digits_auto_set(self):
        r = self._make("321")
        assert r.sorted_digits == "123"

    def test_winning_number_normalized(self):
        r = self._make("1-2-3")
        assert r.winning_number == "123"

    def test_leading_zeros_in_winning_number(self):
        r = self._make("034")
        assert r.winning_number == "034"
        assert r.winning_number[0] == "0"

    def test_canonical_key_format(self):
        r = self._make("123")
        assert r.canonical_key == "GA|pick3|2024-03-15|midday"

    def test_canonical_key_uses_canonical_draw_time(self):
        r = self._make("123", draw_time="evening")
        assert r.canonical_key == "GA|pick3|2024-03-15|evening"


class TestDateRangeMonths:
    def test_single_month(self):
        result = list(date_range_months(date(2024, 3, 1), date(2024, 3, 31)))
        assert result == [(2024, 3)]

    def test_two_months(self):
        result = list(date_range_months(date(2024, 3, 15), date(2024, 4, 10)))
        assert result == [(2024, 3), (2024, 4)]

    def test_year_boundary(self):
        result = list(date_range_months(date(2024, 11, 1), date(2025, 2, 28)))
        assert result == [(2024, 11), (2024, 12), (2025, 1), (2025, 2)]

    def test_single_day(self):
        result = list(date_range_months(date(2024, 6, 15), date(2024, 6, 15)))
        assert result == [(2024, 6)]

    def test_start_after_end_empty(self):
        result = list(date_range_months(date(2024, 6, 1), date(2024, 5, 1)))
        assert result == []

    def test_15_year_range_count(self):
        result = list(date_range_months(date(2009, 1, 1), date(2024, 12, 31)))
        assert len(result) == 16 * 12  # 2009-2024 inclusive = 16 years
