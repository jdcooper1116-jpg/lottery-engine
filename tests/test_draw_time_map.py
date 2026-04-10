"""
lottery_engine/tests/test_draw_time_map.py
"""
import pytest
from sources.draw_time_map import normalize_draw_time
from registry.enums import DrawTime


class TestNormalizeDrawTime:
    def test_exact_canonical_values(self):
        for dt in DrawTime:
            assert normalize_draw_time(dt.value) == dt.value

    def test_midday_variants(self):
        for raw in ["Midday", "MIDDAY", "Mid-Day", "mid day", "Noon", "noon", "12PM", "12:29"]:
            assert normalize_draw_time(raw) == DrawTime.MIDDAY, f"Failed: {raw!r}"

    def test_evening_variants(self):
        for raw in ["Evening", "EVENING", "Eve", "Eve.", "6PM", "6:59", "7PM"]:
            assert normalize_draw_time(raw) == DrawTime.EVENING, f"Failed: {raw!r}"

    def test_night_variants(self):
        for raw in ["Night", "NIGHT", "Nite", "Late", "9PM", "9:45", "11PM", "11:34"]:
            assert normalize_draw_time(raw) == DrawTime.NIGHT, f"Failed: {raw!r}"

    def test_morning_variants(self):
        for raw in ["Morning", "MORNING", "Morn", "AM", "A.M."]:
            assert normalize_draw_time(raw) == DrawTime.MORNING, f"Failed: {raw!r}"

    def test_day_variants(self):
        for raw in ["Day", "DAY", "Daytime", "daytime", "Afternoon"]:
            assert normalize_draw_time(raw) == DrawTime.DAY, f"Failed: {raw!r}"

    def test_none_input(self):
        assert normalize_draw_time(None) == DrawTime.UNKNOWN

    def test_empty_string(self):
        assert normalize_draw_time("") == DrawTime.UNKNOWN

    def test_unknown_label(self):
        assert normalize_draw_time("zzz_unknown_zzz") == DrawTime.UNKNOWN

    def test_case_insensitive(self):
        assert normalize_draw_time("MIDDAY") == DrawTime.MIDDAY
        assert normalize_draw_time("midday") == DrawTime.MIDDAY
        assert normalize_draw_time("MiDdAy") == DrawTime.MIDDAY

    def test_whitespace_stripped(self):
        assert normalize_draw_time("  midday  ") == DrawTime.MIDDAY
        assert normalize_draw_time("\tEvening\n") == DrawTime.EVENING

    def test_daytime_maps_to_day_not_daytime(self):
        """Ensure 'daytime' is eliminated in favor of 'day'."""
        result = normalize_draw_time("daytime")
        assert result == DrawTime.DAY
        assert result != "daytime"
