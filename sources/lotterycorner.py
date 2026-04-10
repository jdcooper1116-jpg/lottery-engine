"""
lottery_engine/sources/lotterycorner.py

Parser for lotterycorner.com — secondary / gap-filler / verifier (priority 2).

Page structure (as of 2024):
  Results at /{state}/{game}/{year}-{month:02d}.html
  Typical layout: monthly results table with date column and draw columns.
  Each row: date | midday_number | evening_number (or with night column).
  Rows with missing draws show "-" or empty cells.

Parsing strategy:
  1. Table parse: multi-column month table (common layout)
  2. Alternate table parse: single-draw-per-row layout

Note: This source uses month-based pages. The URL template must include
{year} and {month} zero-padded. Verify slug format per state.
"""
import logging
import re

from bs4 import BeautifulSoup, Tag

from registry.models import SourceJobMapping
from registry.enums import SourceName, SOURCE_PRIORITIES
from sources.base import SourceParser, RawDrawResult, normalize_number, now_utc_iso
from sources.draw_time_map import normalize_draw_time
from sources.lottery_net import _parse_date, _is_valid_number

logger = logging.getLogger(__name__)


class LotteryCornerParser(SourceParser):
    source_name     = SourceName.LOTTERYCORNER
    source_priority = SOURCE_PRIORITIES[SourceName.LOTTERYCORNER]

    def fetch_month(
        self,
        mapping: SourceJobMapping,
        year: int,
        month: int,
    ) -> list[RawDrawResult]:
        url = mapping.build_url(year=year, month=month)
        if not url:
            return []

        resp = self._get(url)
        if resp is None:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = self._parse_monthly_table(soup, mapping, url)

        if not results:
            results = self._parse_row_per_draw(soup, mapping, url)

        results = [
            r for r in results
            if r.draw_date.startswith(f"{year}-{month:02d}")
        ]

        logger.info("  lotterycorner: %d results for %s %s %d/%02d",
                    len(results), mapping.job_def.state,
                    mapping.job_def.game_type, year, month)
        return results

    # ------------------------------------------------------------------
    # Strategy 1: monthly table (date | midday | evening | [night])
    # ------------------------------------------------------------------
    def _parse_monthly_table(
        self,
        soup: BeautifulSoup,
        mapping: SourceJobMapping,
        url: str,
    ) -> list[RawDrawResult]:
        results: list[RawDrawResult] = []
        now = now_utc_iso()

        tables = soup.find_all("table")
        for table in tables:
            headers_raw = _get_headers(table)
            if not headers_raw:
                continue
            headers_lower = [h.lower() for h in headers_raw]

            # Need at least a date column
            if not any("date" in h or "day" in h for h in headers_lower):
                continue

            date_idx = next((i for i, h in enumerate(headers_lower) if "date" in h or "day" in h), None)
            if date_idx is None:
                continue

            # Map non-date columns to draw times
            time_cols: dict[int, str] = {}
            for i, h in enumerate(headers_raw):
                if i == date_idx:
                    continue
                h_norm = h.lower().strip()
                if h_norm in ("", "#"):
                    continue
                canonical = normalize_draw_time(h_norm)
                if canonical != "unknown":
                    time_cols[i] = (canonical, h_norm)
                elif any(k in h_norm for k in ["draw", "number", "result", "winning", "pick"]):
                    # Single draw time page — use mapping's draw time
                    time_cols[i] = (mapping.job_def.draw_time, h_norm)

            if not time_cols:
                continue

            body = table.find("tbody") or table
            for row in body.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) <= date_idx:
                    continue
                raw_date = cells[date_idx].get_text(strip=True)
                draw_date = _parse_date(raw_date)
                if not draw_date:
                    continue

                for col_idx, (canonical_time, raw_label) in time_cols.items():
                    if col_idx >= len(cells):
                        continue
                    raw_number = cells[col_idx].get_text(strip=True)
                    number = normalize_number(raw_number)
                    # Skip blank/placeholder cells
                    if not number or raw_number.strip() in ("-", "—", "N/A", "TBD", ""):
                        continue
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
                        raw_draw_time_label=raw_label,
                        scraped_at=now,
                    ))

        return results

    # ------------------------------------------------------------------
    # Strategy 2: one row per draw (date | time_label | number)
    # ------------------------------------------------------------------
    def _parse_row_per_draw(
        self,
        soup: BeautifulSoup,
        mapping: SourceJobMapping,
        url: str,
    ) -> list[RawDrawResult]:
        results: list[RawDrawResult] = []
        now = now_utc_iso()

        for table in soup.find_all("table"):
            headers_raw = _get_headers(table)
            if not headers_raw:
                continue
            headers_lower = [h.lower() for h in headers_raw]

            date_idx   = next((i for i, h in enumerate(headers_lower) if "date" in h), None)
            time_idx   = next((i for i, h in enumerate(headers_lower)
                               if "time" in h or "draw" in h), None)
            number_idx = next((i for i, h in enumerate(headers_lower)
                               if "number" in h or "result" in h or "winning" in h), None)

            if date_idx is None or number_idx is None:
                continue

            body = table.find("tbody") or table
            for row in body.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) <= max(filter(None, [date_idx, time_idx, number_idx])):
                    continue
                raw_date = cells[date_idx].get_text(strip=True)
                draw_date = _parse_date(raw_date)
                if not draw_date:
                    continue

                raw_time = cells[time_idx].get_text(strip=True) if time_idx is not None else ""
                canonical_time = normalize_draw_time(raw_time) if raw_time else mapping.job_def.draw_time

                raw_number = cells[number_idx].get_text(strip=True)
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
        return results


def _get_headers(table: Tag) -> list[str]:
    thead = table.find("thead")
    row = (thead or table).find("tr")
    if not row:
        return []
    return [th.get_text(strip=True) for th in row.find_all(["th", "td"])]
