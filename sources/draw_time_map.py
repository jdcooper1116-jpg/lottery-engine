"""
lottery_engine/sources/draw_time_map.py

THE single normalization map for raw source draw-time labels -> canonical DrawTime.
This file is the only place draw-time normalization logic lives.
All source parsers import from here; none maintain their own maps.

To add a new raw label: add it to RAW_LABEL_MAP below.
To diagnose unknown values: run python -m sources.draw_time_map <label>

Canonical values: morning | day | midday | evening | night | unknown
"""
import re
from registry.enums import DrawTime

# ------------------------------------------------------------------
# Raw label -> canonical DrawTime
# Add source-specific variants here as they are discovered.
# Keys are lowercase stripped; matching is case-insensitive.
# ------------------------------------------------------------------
_RAW_LABEL_MAP: dict[str, str] = {
    # morning variants
    "morning":        DrawTime.MORNING,
    "morn":           DrawTime.MORNING,
    "early":          DrawTime.MORNING,
    "am":             DrawTime.MORNING,
    "a.m.":           DrawTime.MORNING,
    "early morning":  DrawTime.MORNING,

    # day variants (generic daytime, not noon-aligned)
    "day":            DrawTime.DAY,
    "daytime":        DrawTime.DAY,
    "afternoon":      DrawTime.DAY,
    "daily":          DrawTime.DAY,

    # midday variants
    "midday":         DrawTime.MIDDAY,
    "mid-day":        DrawTime.MIDDAY,
    "mid day":        DrawTime.MIDDAY,
    "noon":           DrawTime.MIDDAY,
    "lunchtime":      DrawTime.MIDDAY,
    "lunch":          DrawTime.MIDDAY,
    "12pm":           DrawTime.MIDDAY,
    "12:00":          DrawTime.MIDDAY,
    "12:29":          DrawTime.MIDDAY,
    "12:30":          DrawTime.MIDDAY,
    "1pm":            DrawTime.MIDDAY,
    "1:30":           DrawTime.MIDDAY,
    "1:30pm":         DrawTime.MIDDAY,
    "mid":            DrawTime.MIDDAY,

    # evening variants
    "evening":        DrawTime.EVENING,
    "eve":            DrawTime.EVENING,
    "eve.":           DrawTime.EVENING,
    "evng":           DrawTime.EVENING,
    "early evening":  DrawTime.EVENING,
    "6pm":            DrawTime.EVENING,
    "6:59":           DrawTime.EVENING,
    "7pm":            DrawTime.EVENING,
    "7:00":           DrawTime.EVENING,
    "7:29":           DrawTime.EVENING,
    "7:30":           DrawTime.EVENING,

    # night variants
    "night":          DrawTime.NIGHT,
    "nite":           DrawTime.NIGHT,
    "late":           DrawTime.NIGHT,
    "late night":     DrawTime.NIGHT,
    "pm":             DrawTime.NIGHT,    # bare "pm" with no hour = assume night
    "9pm":            DrawTime.NIGHT,
    "9:45":           DrawTime.NIGHT,
    "10pm":           DrawTime.NIGHT,
    "11pm":           DrawTime.NIGHT,
    "11:34":          DrawTime.NIGHT,
    "midnight":       DrawTime.NIGHT,
}


def normalize_draw_time(raw_label: str | None) -> str:
    """
    Normalize a raw source draw-time label to a canonical DrawTime value.

    Steps:
    1. Strip whitespace, lowercase.
    2. Direct lookup in _RAW_LABEL_MAP.
    3. Partial match against canonical names.
    4. Fallback to DrawTime.UNKNOWN.

    Always returns a string (never raises).
    """
    if not raw_label:
        return DrawTime.UNKNOWN

    cleaned = raw_label.strip().lower()

    # Direct lookup
    if cleaned in _RAW_LABEL_MAP:
        return _RAW_LABEL_MAP[cleaned]

    # Remove punctuation and retry
    stripped = re.sub(r"[^a-z0-9 ]", "", cleaned).strip()
    if stripped in _RAW_LABEL_MAP:
        return _RAW_LABEL_MAP[stripped]

    # Partial substring match against canonical names (longest match wins)
    canonical_order = [DrawTime.MIDDAY, DrawTime.MORNING, DrawTime.EVENING, DrawTime.NIGHT, DrawTime.DAY]
    for canonical in canonical_order:
        if canonical.value in stripped:
            return canonical.value

    # Time-of-day pattern: extract hour
    hour_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", stripped)
    if hour_match:
        hour = int(hour_match.group(1))
        meridiem = hour_match.group(3) or ""
        if meridiem == "pm" and hour != 12:
            hour += 12
        if 9 <= hour <= 11:
            return DrawTime.MORNING
        if 11 <= hour <= 13:
            return DrawTime.MIDDAY
        if 13 <= hour <= 18:
            return DrawTime.DAY
        if 17 <= hour <= 21:
            return DrawTime.EVENING
        if hour >= 21 or hour < 5:
            return DrawTime.NIGHT

    return DrawTime.UNKNOWN


def is_unknown(draw_time: str) -> bool:
    return draw_time == DrawTime.UNKNOWN


if __name__ == "__main__":
    import sys
    label = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "midday"
    result = normalize_draw_time(label)
    print(f"Input:  {label!r}")
    print(f"Output: {result!r}")
