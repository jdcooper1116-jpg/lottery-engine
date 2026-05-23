"""
lottery_engine/sources/lotteryusa.py

Parser for lotteryusa.com — near-current supplemental source (priority 3).

Page structure (as of 2024):
  lotteryusa.com uses a single-game results page with recent results.
  Typical layout: results list/table showing last 30–90 days.
  Each entry: date | draw_time_label | winning_number

This source is limited to recent coverage (source_min_year=2018 typically).
It is used only for gap-filling recent dates not yet in higher-priority sources.

Parsing strategy:
  1. JSON/API response embedded in page (lotteryusa embeds data as JS object)
  2. HTML table parse
  3. List-based result entries
"""
import json
import logging
import re

from bs4 import BeautifulSoup

from registry.models import SourceJobMapping
from registry.enums import SourceName, SOURCE_PRIORITIES
from sources.base import SourceParser, RawDrawResult, normalize_number, now_utc_iso
from sources.draw_time_map import normalize_draw_time
from sources.lottery_net import _parse_date, _is_valid_number

logger = logging.getLogger(__name__)

# lotteryusa.com embeds results in a JS variable or JSON block
_JS_DATA_PATTERN = re.compile(
    r'(?:window\.__INITIAL_STATE__|var\s+resultsData|"results"\s*:)\s*=?\s*(\[.*?\]|\{.*?\})',
    re.DOTALL,
)


class LotteryUSAParser(SourceParser):
    source_name     = SourceName.LOTTERYUSA
    source_priority = SOURCE_PRIORITIES[SourceName.LOTTERYUSA]

    def fetch_month(
        self,
        mapping: SourceJobMapping,
        year: int,
        month: int,
    ) -> list[RawDrawResult]:
        """
        lotteryusa.com doesn't have per-month pages.
        We fetch the game page and extract available recent results.
        The orchestrator calls this once per month but the same URL
        returns all recent results; deduplication happens via canonical_key.
        """
        url = mapping.url_template or mapping.build_url(year=year, month=month)
        if not url:
            return []

        resp = self._get(url)
        if resp is None:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        results = self._parse_embedded_json(resp.text, soup, mapping, url)
        if not results:
            results = self._parse_html_table(soup, mapping, url)
        if not results:
            results = self._parse_result_entries(soup, mapping, url)

        # Filter to requested month/year
        results = [
            r for r in results
            if r.draw_date.startswith(f"{year}-{month:02d}")
        ]

        logger.info("  lotteryusa: %d results for %s %s %d/%02d",
                    len(results), mapping.job_def.state,
                    mapping.job_def.game_type, year, month)
        return results

    # ------------------------------------------------------------------
    # Strategy 1: embedded JSON / JS variable
    # ------------------------------------------------------------------
    def _parse_embedded_json(
        self,
        html: str,
        soup: BeautifulSoup,
        mapping: SourceJobMapping,
        url: str,
    ) -> list[RawDrawResult]:
        results: list[RawDrawResult] = []
        now = now_utc_iso()

        # Try <script type="application/json"> blocks first
        for script in soup.find_all("script", type="application/json"):
            try:
                data = json.loads(script.string or "")
                rows = _extract_results_from_json(data)
                for row in rows:
                    r = _json_row_to_result(row, mapping, url, now)
                    if r:
                        results.append(r)
            except Exception:
                continue

        if results:
            return results

        # Try JS variable pattern in page source
        for match in _JS_DATA_PATTERN.finditer(html):
            try:
                data = json.loads(match.group(1))
                rows = _extract_results_from_json(data)
                for row in rows:
                    r = _json_row_to_result(row, mapping, url, now)
                    if r:
                        results.append(r)
            except Exception:
                continue

        return results

    # ------------------------------------------------------------------
    # Strategy 2: HTML table
    # ------------------------------------------------------------------
    def _parse_html_table(
        self,
        soup: BeautifulSoup,
        mapping: SourceJobMapping,
        url: str,
    ) -> list[RawDrawResult]:
        results: list[RawDrawResult] = []
        now = now_utc_iso()

        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True).lower()
                       for th in (table.find("thead") or table).find_all(["th", "td"])[:6]]
            if not any("date" in h for h in headers):
                continue

            date_idx   = next((i for i, h in enumerate(headers) if "date" in h), None)
            time_idx   = next((i for i, h in enumerate(headers) if "time" in h or "draw" in h), None)
            number_idx = next((i for i, h in enumerate(headers)
                               if any(k in h for k in ["number", "result", "winning"])), None)
            if date_idx is None:
                continue

            body = table.find("tbody") or table
            for row in body.find_all("tr"):
                cells = row.find_all(["td", "th"])
                try:
                    raw_date = cells[date_idx].get_text(strip=True)
                    draw_date = _parse_date(raw_date)
                    if not draw_date:
                        continue

                    raw_time = cells[time_idx].get_text(strip=True) if time_idx and time_idx < len(cells) else ""
                    # Use "unknown" when the page carries no draw_time label.
                    # Callers that need a specific draw_time will filter these out.
                    canonical_time = normalize_draw_time(raw_time) if raw_time else "unknown"

                    num_col = number_idx if number_idx is not None else _find_number_cell(cells, mapping.job_def.game_type)
                    if num_col is None or num_col >= len(cells):
                        continue
                    raw_number = cells[num_col].get_text(strip=True)
                    number = normalize_number(raw_number)
                    if not _is_valid_number(number, mapping.job_def.game_type):
                        continue

                    results.append(RawDrawResult(
                        state=mapping.job_def.state,
                        game_type=mapping.job_def.game_type,
                        draw_date=draw_date,
                        draw_time=canonical_time,
                        winning_number=number,
                        source_name=self.source_name,
                        source_priority=self.source_priority,
                        source_url=url,
                        raw_draw_time_label=raw_time,
                        scraped_at=now,
                    ))
                except (IndexError, AttributeError):
                    continue

        return results

    # ------------------------------------------------------------------
    # Strategy 3: result entry divs
    # ------------------------------------------------------------------
    def _parse_result_entries(
        self,
        soup: BeautifulSoup,
        mapping: SourceJobMapping,
        url: str,
    ) -> list[RawDrawResult]:
        results: list[RawDrawResult] = []
        now = now_utc_iso()

        entries = soup.find_all(
            class_=re.compile(r"result|draw|winning|lottery-number", re.I)
        )
        for entry in entries:
            try:
                date_el   = entry.find(class_=re.compile(r"date", re.I)) or entry.find("time")
                number_el = entry.find(class_=re.compile(r"number|result|ball", re.I))
                time_el   = entry.find(class_=re.compile(r"time|draw.?time", re.I))

                if not date_el or not number_el:
                    continue

                raw_date = date_el.get("datetime") or date_el.get_text(strip=True)
                draw_date = _parse_date(str(raw_date))
                if not draw_date:
                    continue

                raw_number = number_el.get_text(strip=True)
                number = normalize_number(raw_number)
                if not _is_valid_number(number, mapping.job_def.game_type):
                    continue

                raw_time = time_el.get_text(strip=True) if time_el else ""
                canonical_time = normalize_draw_time(raw_time) if raw_time else "unknown"

                results.append(RawDrawResult(
                    state=mapping.job_def.state,
                    game_type=mapping.job_def.game_type,
                    draw_date=draw_date,
                    draw_time=canonical_time,
                    winning_number=number,
                    source_name=self.source_name,
                    source_priority=self.source_priority,
                    source_url=url,
                    raw_draw_time_label=raw_time,
                    scraped_at=now,
                ))
            except Exception:
                continue

        return results


# ------------------------------------------------------------------
# JSON utility helpers
# ------------------------------------------------------------------

def _extract_results_from_json(data) -> list[dict]:
    """Recursively find a list of draw result dicts in a JSON blob."""
    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return data
        for item in data:
            found = _extract_results_from_json(item)
            if found:
                return found
    elif isinstance(data, dict):
        for key in ("results", "draws", "data", "items", "winning_numbers"):
            if key in data:
                found = _extract_results_from_json(data[key])
                if found:
                    return found
    return []


def _json_row_to_result(
    row: dict,
    mapping: SourceJobMapping,
    url: str,
    now: str,
) -> RawDrawResult | None:
    raw_date = row.get("date") or row.get("draw_date") or row.get("drawDate")
    raw_number = (
        row.get("number") or row.get("winning_number") or
        row.get("winningNumber") or row.get("result")
    )
    raw_time = row.get("draw_time") or row.get("drawTime") or row.get("time") or ""

    if not raw_date or not raw_number:
        return None

    draw_date = _parse_date(str(raw_date))
    if not draw_date:
        return None

    number = normalize_number(str(raw_number))
    if not _is_valid_number(number, mapping.job_def.game_type):
        return None

    canonical_time = normalize_draw_time(str(raw_time)) if raw_time else "unknown"

    return RawDrawResult(
        state=mapping.job_def.state,
        game_type=mapping.job_def.game_type,
        draw_date=draw_date,
        draw_time=canonical_time,
        winning_number=number,
        source_name=SourceName.LOTTERYUSA,
        source_priority=SOURCE_PRIORITIES[SourceName.LOTTERYUSA],
        source_url=url,
        raw_draw_time_label=str(raw_time),
        scraped_at=now,
    )


def _find_number_cell(cells, game_type: str) -> int | None:
    expected = 3 if game_type == "pick3" else 4
    for i, cell in enumerate(cells):
        text = normalize_number(cell.get_text(strip=True))
        if len(text) == expected:
            return i
    return None
