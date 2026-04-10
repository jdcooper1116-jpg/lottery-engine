"""
lottery_engine/sources/lottery_net.py

Parser for lottery.net — primary historical source (priority 1).

URL pattern:
    https://www.lottery.net/{state_slug}/{game_slug}/numbers/{year}

Each URL is a per-draw-time yearly page. Georgia example slugs:
    georgia/cash-3-midday/numbers/2024
    georgia/cash-3-evening/numbers/2024
    georgia/cash-3-night/numbers/2024
    georgia/cash-4-midday/numbers/2024
    georgia/cash-4-evening/numbers/2024
    georgia/cash-4-night/numbers/2024

Because pages are yearly, this parser fetches once and caches per URL.
fetch_month() slices cached results to the requested (year, month).

draw_time is taken directly from mapping.job_def.draw_time — each page
covers exactly one draw time so no splitting is needed.

Observed live page structure (2024):
    Heading:  "Georgia Cash 3 Midday Numbers 2024"
    Sub-head: "Past Result Date Numbers"
    Then repeated draw blocks:
        weekday line     e.g. "Tuesday"
        date line        e.g. "December 31, 2024"
        digits line      e.g. "3 7 2"  or  "8 2 9 5"  (space-separated)

Parse strategies (tried in order, first non-empty result wins):
    1. _parse_text_scan     — primary: walks text nodes for date+number pairs
    2. _parse_ball_list     — CSS ball/digit element lists
    3. _parse_results_table — HTML <table> layouts
    4. _parse_json_ld       — <script type="application/ld+json">
"""
from __future__ import annotations
import json
import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from registry.models import SourceJobMapping
from registry.enums import SourceName, SOURCE_PRIORITIES
from sources.base import SourceParser, RawDrawResult, normalize_number, now_utc_iso

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Month name regex used in date extraction
# ---------------------------------------------------------------------------
_MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|"
    "September|October|November|December|"
    "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
)
_DATE_IN_TEXT_RE = re.compile(
    rf"(?:{_MONTH_NAMES})\s+\d{{1,2}},?\s+\d{{4}}",
    re.IGNORECASE,
)

_DATE_FMTS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%B %d, %Y",    # December 31, 2024
    "%B %d %Y",     # December 31 2024  (no comma)
    "%b %d, %Y",    # Dec 31, 2024
    "%b %d %Y",     # Dec 31 2024
    "%m-%d-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
]

_SKIP_TAGS = {"script", "style", "noscript", "head", "title", "meta", "link"}


# ---------------------------------------------------------------------------
# Parser class
# ---------------------------------------------------------------------------

class LotteryNetParser(SourceParser):
    source_name     = SourceName.LOTTERY_NET
    source_priority = SOURCE_PRIORITIES[SourceName.LOTTERY_NET]

    def __init__(self) -> None:
        super().__init__()
        # Cache: url -> parsed results for the full year page
        self._page_cache: dict[str, list[RawDrawResult]] = {}

    # -----------------------------------------------------------------------
    # Public interface
    # -----------------------------------------------------------------------

    def fetch_month(
        self,
        mapping: SourceJobMapping,
        year: int,
        month: int,
    ) -> list[RawDrawResult]:
        """
        Return results for one (year, month).
        Fetches the yearly URL once (cached), then slices to the month.
        """
        url = mapping.build_url(year=year, month=month)
        if not url:
            logger.warning("No URL template for %s", mapping.job_def.draw_label)
            return []

        if url not in self._page_cache:
            self._page_cache[url] = self._fetch_year_page(url, mapping)

        prefix = f"{year}-{month:02d}"
        results = [r for r in self._page_cache[url] if r.draw_date.startswith(prefix)]

        logger.info(
            "  lottery.net: %d rows  %s/%s/%s  %d/%02d  [%s]",
            len(results),
            mapping.job_def.state, mapping.job_def.game_type, mapping.job_def.draw_time,
            year, month, mapping.source_game_slug,
        )
        return results

    def clear_cache(self) -> None:
        self._page_cache.clear()

    # -----------------------------------------------------------------------
    # Year-page fetch and strategy dispatch
    # -----------------------------------------------------------------------

    def _fetch_year_page(
        self,
        url: str,
        mapping: SourceJobMapping,
    ) -> list[RawDrawResult]:
        resp = self._get(url)
        if resp is None:
            logger.warning("lottery.net: failed to fetch %s", url)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        for strategy in (
            self._parse_text_scan,
            self._parse_ball_list,
            self._parse_results_table,
            self._parse_json_ld,
        ):
            try:
                results = strategy(soup, mapping, url)
                if results:
                    logger.debug(
                        "  lottery.net: %s → %d rows for %s",
                        strategy.__name__, len(results), url,
                    )
                    return results
            except Exception as exc:
                logger.debug("  lottery.net: %s failed for %s: %s",
                             strategy.__name__, url, exc)

        logger.warning("lottery.net: all strategies returned 0 rows for %s", url)
        return []

    # -----------------------------------------------------------------------
    # Strategy 1 (PRIMARY): text-node scan
    #
    # Walks every visible text node in document order.
    # When a node contains a recognisable date, scans the next few nodes
    # for a digit string of the expected length.
    #
    # Handles the observed lottery.net structure:
    #   "Tuesday"           ← weekday line  (skip)
    #   "December 31, 2024" ← date line     (anchor)
    #   "3 7 2"             ← digits line   (number, space-separated)
    #
    # Also handles:
    #   "Tuesday, December 31, 2024" (combined weekday+date in one node)
    #   "0 1 5" → "015"  (leading zeros preserved via string join)
    #   Individual-digit sibling nodes: "3" "7" "2" → "372"
    # -----------------------------------------------------------------------

    def _parse_text_scan(
        self,
        soup: BeautifulSoup,
        mapping: SourceJobMapping,
        url: str,
    ) -> list[RawDrawResult]:
        now = now_utc_iso()
        canonical_time = mapping.job_def.draw_time
        expected = 3 if mapping.job_def.game_type == "pick3" else 4

        # Collect all visible text nodes in document order
        texts: list[str] = [
            str(node).strip()
            for node in soup.find_all(string=True)
            if node.parent.name not in _SKIP_TAGS
            and str(node).strip()
        ]

        results: list[RawDrawResult] = []
        seen_keys: set[str] = set()
        i = 0

        while i < len(texts):
            draw_date = _parse_date_text(texts[i])
            if not draw_date:
                i += 1
                continue

            # Scan ahead up to 6 nodes for a winning number
            found = False
            for j in range(i + 1, min(i + 7, len(texts))):
                t = texts[j]

                # Case A: the node is a space-separated or compact digit string
                number = _try_extract_number(t, expected)
                if number:
                    r = _make_result(mapping, draw_date, canonical_time, number, url, now)
                    if r.canonical_key not in seen_keys:
                        seen_keys.add(r.canonical_key)
                        results.append(r)
                    i = j + 1
                    found = True
                    break

                # Case B: this node is a single digit — check if the next
                # (expected - 1) nodes are also single digits → concat them
                if t.isdigit() and len(t) == 1:
                    window_end = j + expected
                    if window_end <= len(texts):
                        window = texts[j:window_end]
                        if all(w.isdigit() and len(w) == 1 for w in window):
                            number = "".join(window)  # preserves order incl. "0"
                            r = _make_result(mapping, draw_date, canonical_time, number, url, now)
                            if r.canonical_key not in seen_keys:
                                seen_keys.add(r.canonical_key)
                                results.append(r)
                            i = window_end
                            found = True
                            break

                # If we hit another date, stop looking for this date's number
                if _parse_date_text(t):
                    break

            if not found:
                i += 1

        return results

    # -----------------------------------------------------------------------
    # Strategy 2: CSS ball/digit element list
    # -----------------------------------------------------------------------

    def _parse_ball_list(
        self,
        soup: BeautifulSoup,
        mapping: SourceJobMapping,
        url: str,
    ) -> list[RawDrawResult]:
        now = now_utc_iso()
        canonical_time = mapping.job_def.draw_time
        expected = 3 if mapping.job_def.game_type == "pick3" else 4
        results: list[RawDrawResult] = []

        items = soup.find_all(
            lambda tag: tag.name in ("li", "div", "article")
            and tag.get("class")
            and any(re.search(r"result|draw|item|entry", c, re.I)
                    for c in tag.get("class", []))
        )
        for item in items:
            draw_date = _extract_date_from_element(item)
            if not draw_date:
                continue

            balls = item.find_all(
                lambda t: t.name in ("li", "span", "div")
                and t.get("class")
                and any(re.search(r"ball|digit|num", c, re.I)
                        for c in t.get("class", []))
            )
            if balls:
                raw_num = "".join(b.get_text(strip=True) for b in balls)
            else:
                raw_num = _find_number_text_in(item, expected)
                if not raw_num:
                    continue

            number = normalize_number(raw_num)
            if not _valid(number, expected):
                continue

            results.append(_make_result(mapping, draw_date, canonical_time, number, url, now))
        return results

    # -----------------------------------------------------------------------
    # Strategy 3: HTML table
    # -----------------------------------------------------------------------

    def _parse_results_table(
        self,
        soup: BeautifulSoup,
        mapping: SourceJobMapping,
        url: str,
    ) -> list[RawDrawResult]:
        now = now_utc_iso()
        canonical_time = mapping.job_def.draw_time
        expected = 3 if mapping.job_def.game_type == "pick3" else 4
        results: list[RawDrawResult] = []

        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True).lower()
                       for th in (table.find("thead") or table).find_all(["th", "td"])[:6]]
            date_col   = _col_idx(headers, ("date", "day", "drawn")) or 0
            number_col = _col_idx(headers, ("number", "result", "winning", "draw", "pick")) or 1

            body = table.find("tbody") or table
            for row in body.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(date_col, number_col):
                    continue
                draw_date = _parse_date_text(cells[date_col].get_text(strip=True))
                if not draw_date:
                    continue

                num_cell = cells[number_col]
                balls = num_cell.find_all(
                    lambda t: t.name in ("span", "li", "div")
                    and any(re.search(r"ball|digit", c, re.I)
                            for c in t.get("class", []))
                )
                raw_num = (
                    "".join(b.get_text(strip=True) for b in balls)
                    if balls
                    else num_cell.get_text(strip=True)
                )
                number = normalize_number(raw_num)
                if not _valid(number, expected):
                    continue
                results.append(_make_result(mapping, draw_date, canonical_time, number, url, now))
        return results

    # -----------------------------------------------------------------------
    # Strategy 4: JSON-LD
    # -----------------------------------------------------------------------

    def _parse_json_ld(
        self,
        soup: BeautifulSoup,
        mapping: SourceJobMapping,
        url: str,
    ) -> list[RawDrawResult]:
        now = now_utc_iso()
        canonical_time = mapping.job_def.draw_time
        expected = 3 if mapping.job_def.game_type == "pick3" else 4
        results: list[RawDrawResult] = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    raw_date   = item.get("startDate") or item.get("date")
                    raw_number = item.get("result") or item.get("name") or item.get("number")
                    if not raw_date or not raw_number:
                        continue
                    draw_date = _parse_date_text(str(raw_date))
                    if not draw_date:
                        continue
                    number = normalize_number(str(raw_number))
                    if not _valid(number, expected):
                        continue
                    results.append(_make_result(mapping, draw_date, canonical_time, number, url, now))
            except Exception:
                continue
        return results


# ---------------------------------------------------------------------------
# Shared parsing utilities
# (exported for use by lotterycorner.py and lotteryusa.py)
# ---------------------------------------------------------------------------

def _parse_date_text(raw: str) -> str | None:
    """
    Parse a raw string to YYYY-MM-DD.

    Handles:
      - "December 31, 2024"          → "2024-12-31"
      - "Tuesday, December 31, 2024" → "2024-12-31"  (weekday stripped)
      - "December 31 2024"           → "2024-12-31"  (no comma)
      - "Dec 31, 2024"               → "2024-12-31"
      - "2024-12-31"                 → "2024-12-31"
      - "12/31/2024"                 → "2024-12-31"

    Returns None if no date can be parsed.
    """
    if not raw:
        return None
    raw = raw.strip()

    # Fast path: ISO date prefix
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)

    # Strip a leading weekday: "Tuesday, December 31, 2024" → "December 31, 2024"
    raw = re.sub(
        r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
        r"|Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*",
        "", raw, flags=re.IGNORECASE,
    ).strip()

    # Try each explicit format
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Last resort: find "Month DD, YYYY" or "Month DD YYYY" anywhere in the string
    m = _DATE_IN_TEXT_RE.search(raw)
    if m:
        for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                return datetime.strptime(m.group(0).strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

    return None


# Keep alias so other modules that do `from sources.lottery_net import _parse_date`
# still work without changes.
_parse_date = _parse_date_text


def _try_extract_number(text: str, expected_len: int) -> str | None:
    """
    Extract a lottery number from text, handling:
      "3 7 2"    → "372"   (space-separated single digits)
      "0 1 5"    → "015"   (leading zero via string join, NOT int cast)
      "8 2 9 5"  → "8295"  (pick-4 spaced)
      "372"      → "372"   (already compact)
      "3-7-2"    → "372"   (dash-separated)

    Returns None if text cannot be interpreted as an expected_len number.
    """
    text = text.strip()
    if not text:
        return None

    # Space-separated single digits: each part is exactly one digit
    parts = text.split()
    if (len(parts) == expected_len
            and all(len(p) == 1 and p.isdigit() for p in parts)):
        return "".join(parts)   # "0 1 5" → "015"  leading zero kept

    # Compact or punctuation-separated ("372", "3-7-2", "3.7.2")
    num = normalize_number(text)   # strips non-digits, preserves leading zeros
    if len(num) == expected_len and num.isdigit():
        return num

    return None


def _extract_date_from_element(el: Tag) -> str | None:
    """Try common date locations inside an element."""
    t = el.find("time")
    if t:
        r = _parse_date_text(t.get("datetime") or t.get_text(strip=True))
        if r:
            return r
    for child in el.find_all(class_=re.compile(r"\bdate\b|\bday\b", re.I)):
        r = _parse_date_text(child.get_text(strip=True))
        if r:
            return r
    for attr in ("data-date", "data-draw-date", "datetime"):
        val = el.get(attr)
        if val:
            r = _parse_date_text(str(val))
            if r:
                return r
    return None


def _find_number_text_in(el: Tag, expected_len: int) -> str | None:
    for child in el.find_all(class_=re.compile(r"number|result|winning|pick|ball", re.I)):
        r = _try_extract_number(child.get_text(strip=True), expected_len)
        if r:
            return r
    for text in el.stripped_strings:
        r = _try_extract_number(text, expected_len)
        if r:
            return r
    return None


def _valid(number: str, expected_len: int) -> bool:
    return bool(number) and number.isdigit() and len(number) == expected_len


# Alias used by lotterycorner.py and lotteryusa.py
def _is_valid_number(number: str, game_type: str) -> bool:
    expected = 3 if game_type == "pick3" else 4
    return _valid(number, expected)


def _col_idx(headers: list[str], keywords: tuple) -> int | None:
    for i, h in enumerate(headers):
        if any(k in h for k in keywords):
            return i
    return None


def _table_headers(table: Tag) -> list[str]:
    thead = table.find("thead")
    row = (thead or table).find("tr")
    if not row:
        return []
    return [th.get_text(strip=True).lower() for th in row.find_all(["th", "td"])]


def _make_result(
    mapping: SourceJobMapping,
    draw_date: str,
    draw_time: str,
    winning_number: str,
    url: str,
    scraped_at: str,
    raw_label: str = "",
) -> RawDrawResult:
    return RawDrawResult(
        state=mapping.job_def.state,
        game_type=mapping.job_def.game_type,
        draw_date=draw_date,
        draw_time=draw_time,
        winning_number=winning_number,
        source_name=SourceName.LOTTERY_NET,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERY_NET],
        source_url=url,
        raw_draw_time_label=raw_label or mapping.source_draw_time_label or draw_time,
        scraped_at=scraped_at,
    )
