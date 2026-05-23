"""
lottery_engine/sources/base.py
Abstract base class for all source parsers plus shared utilities.
"""
from __future__ import annotations
import re
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Iterator

import requests
from requests import Session

from registry.models import SourceJobMapping
from sources.draw_time_map import normalize_draw_time

logger = logging.getLogger(__name__)

# Default HTTP session settings
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LotteryEngine/2.0; historical data research)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = 60      # increased from 30 — prevents premature timeout on slow sources
RATE_LIMIT_DELAY = 1.5   # seconds between requests to same host
RETRY_ATTEMPTS   = 3     # retry count for timeout/connection errors
RETRY_BACKOFF    = 2.0   # seconds; doubles each attempt


@dataclass
class RawDrawResult:
    """
    A single draw result as returned by a source parser.
    All fields are normalized (leading zeros preserved, draw_time canonical).
    This gets written to draw_observations by the orchestrator.
    """
    state:               str
    game_type:           str
    draw_date:           str         # YYYY-MM-DD
    draw_time:           str         # canonical enum
    winning_number:      str         # plain text, leading zeros preserved
    source_name:         str
    source_priority:     int
    source_url:          str
    raw_draw_time_label: str         # original label before normalization
    scraped_at:          str         # ISO-8601 UTC
    digit_count:         int         = field(init=False)
    sorted_digits:       str         = field(init=False)

    def __post_init__(self) -> None:
        self.winning_number = normalize_number(self.winning_number)
        self.digit_count    = len(self.winning_number)
        self.sorted_digits  = compute_sorted_digits(self.winning_number)

    @property
    def canonical_key(self) -> str:
        return f"{self.state}|{self.game_type}|{self.draw_date}|{self.draw_time}"


def normalize_number(raw: str) -> str:
    """
    Strip whitespace and non-digit characters.
    PRESERVES leading zeros — never casts to int.
    """
    if not raw:
        return ""
    return re.sub(r"[^\d]", "", raw.strip())


def compute_sorted_digits(number: str) -> str:
    """Sort digits ascending. '312' -> '123', '031' -> '013'."""
    return "".join(sorted(number))


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def date_range_months(start_date: date, end_date: date) -> Iterator[tuple[int, int]]:
    """Yield (year, month) tuples covering start_date..end_date inclusive."""
    y, m = start_date.year, start_date.month
    while (y, m) <= (end_date.year, end_date.month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


class SourceParser(ABC):
    """
    Abstract base for all source parsers.
    Subclasses implement fetch_month() for a single (mapping, year, month).
    The base class orchestrates date ranges and rate limiting.
    """
    source_name: str
    source_priority: int

    def __init__(self) -> None:
        self.session: Session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._last_request_time: float = 0.0
        self.timeout_count:      int   = 0    # incremented on each timeout
        self.error_count:        int   = 0    # incremented on non-timeout errors

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str) -> requests.Response | None:
        """Fetch a URL with rate limiting, retry, and error tracking."""
        self._rate_limit()
        delay = RETRY_BACKOFF
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp
            except (requests.Timeout, requests.ConnectionError) as e:
                self.timeout_count += 1
                logger.warning(
                    "Fetch timeout/connection error for %s (attempt %d/%d): %s",
                    url, attempt, RETRY_ATTEMPTS, e,
                )
                if attempt < RETRY_ATTEMPTS:
                    logger.info("Retrying in %.1fs...", delay)
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error("All %d attempts failed for %s", RETRY_ATTEMPTS, url)
                    return None
            except requests.HTTPError as e:
                # Don't retry fatal HTTP errors (4xx) — only transient failures
                self.error_count += 1
                logger.warning("HTTP error for %s: %s", url, e)
                return None
            except requests.RequestException as e:
                self.error_count += 1
                logger.warning("Fetch failed for %s: %s", url, e)
                return None
        return None

    def fetch_results(
        self,
        mapping: SourceJobMapping,
        start_date: date,
        end_date: date,
    ) -> list[RawDrawResult]:
        """
        Fetch all results for a mapping across a date range.
        Iterates month-by-month and calls fetch_month().
        """
        results: list[RawDrawResult] = []
        for year, month in date_range_months(start_date, end_date):
            if not mapping.covers_year(year):
                logger.debug(
                    "Skipping %s %s %s %d/%02d — outside source coverage",
                    mapping.source_name, mapping.job_def.state,
                    mapping.job_def.game_type, year, month,
                )
                continue
            logger.info(
                "Fetching %s | %s | %s | %d/%02d",
                mapping.source_name, mapping.job_def.state,
                mapping.job_def.game_type, year, month,
            )
            try:
                month_results = self.fetch_month(mapping, year, month)
                # Filter to draw_time matching the mapping's job
                month_results = [
                    r for r in month_results
                    if r.draw_time == mapping.job_def.draw_time
                    or mapping.job_def.draw_time == "unknown"
                ]
                results.extend(month_results)
            except Exception as e:
                logger.error(
                    "Error fetching %s %s %s %d/%02d: %s",
                    mapping.source_name, mapping.job_def.state,
                    mapping.job_def.game_type, year, month, e,
                )
        return results

    @abstractmethod
    def fetch_month(
        self,
        mapping: SourceJobMapping,
        year: int,
        month: int,
    ) -> list[RawDrawResult]:
        """
        Fetch all draw results for one (mapping, year, month).
        Must return ALL draw times found on the page (the caller filters).
        """
        ...
