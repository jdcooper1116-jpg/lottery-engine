#!/usr/bin/env python3
"""
scripts/audit_database_integrity.py

Read-only database integrity audit for all states and games.
Does NOT modify, ingest, or repair anything.

Usage:
    python3 scripts/audit_database_integrity.py
    python3 scripts/audit_database_integrity.py --state GA --game pick3
    python3 scripts/audit_database_integrity.py --recent-days 30 --format markdown

See docs/database_integrity_audit.md for full documentation.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sqlite3
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

VALID_DRAW_TIMES = {"midday", "evening", "night", "morning", "day"}
QUARANTINE_STATUSES = {"anomaly"}

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH     = "HIGH"
SEVERITY_MEDIUM   = "MEDIUM"
SEVERITY_LOW      = "LOW"


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    check_id:    int
    name:        str
    severity:    str
    row_count:   int
    rows:        list[dict] = field(default_factory=list)
    description: str = ""
    ok:          bool = True   # True = no issues found

    def to_summary_dict(self) -> dict:
        return {
            "check_id":   self.check_id,
            "name":       self.name,
            "severity":   self.severity,
            "ok":         self.ok,
            "row_count":  self.row_count,
            "description": self.description,
        }


@dataclass
class AuditSummary:
    db_path:       str
    run_at:        str
    state_filter:  str | None
    game_filter:   str | None
    recent_days:   int
    checks:        list[CheckResult] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for c in self.checks if not c.ok and c.severity == SEVERITY_CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for c in self.checks if not c.ok and c.severity == SEVERITY_HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for c in self.checks if not c.ok and c.severity == SEVERITY_MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for c in self.checks if not c.ok and c.severity == SEVERITY_LOW)

    @property
    def overall_ok(self) -> bool:
        return self.critical_count == 0 and self.high_count == 0


# ---------------------------------------------------------------------------
# DB connection (read-only via URI)
# ---------------------------------------------------------------------------

def open_readonly(db_path: str) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Individual audit checks
# ---------------------------------------------------------------------------

def _state_game_where(state: str | None, game: str | None, prefix: str = "") -> tuple[str, list]:
    parts, params = [], []
    p = f"{prefix}." if prefix else ""
    if state:
        parts.append(f"{p}state = ?")
        params.append(state.upper())
    if game:
        parts.append(f"{p}game_type = ?")
        params.append(game.lower())
    clause = ("WHERE " + " AND ".join(parts)) if parts else ""
    return clause, params


def check_1_duplicate_canonical_keys(conn, state, game) -> CheckResult:
    """Duplicate canonical_key rows in draws (should be impossible due to UNIQUE)."""
    w, p = _state_game_where(state, game)
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT canonical_key, COUNT(*) AS duplicate_count
        FROM draws {w}
        GROUP BY canonical_key
        HAVING duplicate_count > 1
        ORDER BY duplicate_count DESC
        """, p).fetchall())
    return CheckResult(
        check_id=1,
        name="duplicate_canonical_keys_in_draws",
        severity=SEVERITY_CRITICAL,
        row_count=len(rows),
        rows=rows,
        description="canonical_key appears more than once in draws table (UNIQUE constraint violation).",
        ok=len(rows) == 0,
    )


def check_2_same_number_across_draw_times_observations(conn, state, game) -> CheckResult:
    """
    Same winning_number from the SAME source URL across 2+ draw_times for one date.
    Groups by source_url (not just source_name) to distinguish genuine daily-aggregate
    duplication (one URL serving all draw_times) from natural coincidence (same number
    drawn at separate slots, each with its own per-draw-time URL).

    Rows where ALL reconciliation statuses are 'anomaly' are treated as archived/resolved
    evidence and do not trigger CRITICAL — they are flagged all_anomaly=1 in the CSV.
    """
    w, p = _state_game_where(state, game)
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT state, game_type, draw_date, source_name, source_url, winning_number,
               GROUP_CONCAT(DISTINCT draw_time ORDER BY draw_time) AS draw_times,
               COUNT(DISTINCT draw_time)                           AS draw_time_count,
               GROUP_CONCAT(DISTINCT reconciliation_status)       AS statuses
        FROM draw_observations {w}
        GROUP BY state, game_type, draw_date, source_name, source_url, winning_number
        HAVING draw_time_count >= 2
        ORDER BY state, game_type, draw_date
        """, p).fetchall())

    # Annotate each row: anomaly-only groups are archived, not active conflicts.
    active_rows = []
    for r in rows:
        statuses = set((r.get("statuses") or "").split(","))
        r["all_anomaly"] = int(statuses <= {"anomaly", ""})
        if not r["all_anomaly"]:
            active_rows.append(r)

    return CheckResult(
        check_id=2,
        name="same_number_across_draw_times_in_observations",
        severity=SEVERITY_CRITICAL,
        row_count=len(rows),
        rows=rows,
        description=(
            "Same winning_number from the same source URL appears in 2+ draw_time slots for one date. "
            "Groups by source_url to isolate genuine daily-aggregate duplication "
            "(one URL → multiple draw_times) from natural coincidence "
            "(same number, different per-draw-time URLs). "
            f"all_anomaly=1 rows are archived; {len(active_rows)} active group(s) flagged."
        ),
        ok=len(active_rows) == 0,
    )


def check_3_invalid_draw_times(conn, state, game) -> CheckResult:
    """draw_time values outside the known-good set (unknown is only safe when quarantined)."""
    w, p = _state_game_where(state, game)

    # In draws: unknown is never acceptable
    bad_draws = rows_to_dicts(conn.execute(
        f"""
        SELECT 'draws' AS source_table, canonical_key, state, game_type,
               draw_date, draw_time, winning_number, accepted_from_source
        FROM draws {w + (' AND' if w else 'WHERE')} draw_time NOT IN
            ('midday','evening','night','morning','day')
        ORDER BY state, game_type, draw_date
        """, p).fetchall())

    # In observations: unknown is OK only when reconciliation_status = 'anomaly'
    where2, p2 = _state_game_where(state, game)
    bad_obs = rows_to_dicts(conn.execute(
        f"""
        SELECT 'draw_observations' AS source_table, id, canonical_key,
               state, game_type, draw_date, draw_time, winning_number,
               source_name, reconciliation_status
        FROM draw_observations {where2 + (' AND' if where2 else 'WHERE')}
            draw_time NOT IN ('midday','evening','night','morning','day')
            AND reconciliation_status NOT IN ('anomaly')
        ORDER BY state, game_type, draw_date
        """, p2).fetchall())

    rows = bad_draws + bad_obs
    return CheckResult(
        check_id=3,
        name="invalid_draw_time_values",
        severity=SEVERITY_HIGH,
        row_count=len(rows),
        rows=rows,
        description=(
            "draw_time is not one of: midday, evening, night, morning, day. "
            "'unknown' is only acceptable in draw_observations when reconciliation_status=anomaly."
        ),
        ok=len(rows) == 0,
    )


def check_4_pick3_digit_length(conn, state, game) -> CheckResult:
    """Pick 3 winning_number with length != 3."""
    if game and game.lower() == "pick4":
        return CheckResult(4, "pick3_digit_length", SEVERITY_CRITICAL, 0,
                           description="Skipped (game filter = pick4).", ok=True)
    w, p = _state_game_where(state, "pick3")
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT canonical_key, state, game_type, draw_date, draw_time,
               winning_number, digit_count, accepted_from_source
        FROM draws {w}
          AND LENGTH(winning_number) != 3
        ORDER BY state, draw_date
        """, p).fetchall())
    return CheckResult(
        check_id=4,
        name="pick3_wrong_digit_length",
        severity=SEVERITY_CRITICAL,
        row_count=len(rows),
        rows=rows,
        description="Pick 3 draw row where winning_number length != 3.",
        ok=len(rows) == 0,
    )


def check_5_pick4_digit_length(conn, state, game) -> CheckResult:
    """Pick 4 winning_number with length != 4."""
    if game and game.lower() == "pick3":
        return CheckResult(5, "pick4_digit_length", SEVERITY_CRITICAL, 0,
                           description="Skipped (game filter = pick3).", ok=True)
    w, p = _state_game_where(state, "pick4")
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT canonical_key, state, game_type, draw_date, draw_time,
               winning_number, digit_count, accepted_from_source
        FROM draws {w}
          AND LENGTH(winning_number) != 4
        ORDER BY state, draw_date
        """, p).fetchall())
    return CheckResult(
        check_id=5,
        name="pick4_wrong_digit_length",
        severity=SEVERITY_CRITICAL,
        row_count=len(rows),
        rows=rows,
        description="Pick 4 draw row where winning_number length != 4.",
        ok=len(rows) == 0,
    )


def check_6_leading_zero_risk(conn, state, game) -> CheckResult:
    """Numbers shorter than expected for their game — possible int() coercion stripping leading zero."""
    w, p = _state_game_where(state, game)
    # pick3: length 1 or 2 is suspicious (could be 042→42 or 0042→42)
    # pick4: length 1, 2, or 3 is suspicious
    sep = " AND" if w else "WHERE"
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT canonical_key, state, game_type, draw_date, draw_time,
               winning_number, digit_count, accepted_from_source,
               CASE game_type
                   WHEN 'pick3' THEN 3 - LENGTH(winning_number)
                   WHEN 'pick4' THEN 4 - LENGTH(winning_number)
                   ELSE 0
               END AS missing_leading_zeros
        FROM draws {w}
        {sep} (
            (game_type = 'pick3' AND LENGTH(winning_number) < 3)
            OR
            (game_type = 'pick4' AND LENGTH(winning_number) < 4)
        )
        ORDER BY state, game_type, draw_date
        """, p).fetchall())
    return CheckResult(
        check_id=6,
        name="leading_zero_risk",
        severity=SEVERITY_CRITICAL,
        row_count=len(rows),
        rows=rows,
        description=(
            "winning_number is shorter than expected for its game_type. "
            "This suggests a leading zero was stripped by integer coercion during ingest."
        ),
        ok=len(rows) == 0,
    )


def check_7_accepted_with_conflict(conn, state, game) -> CheckResult:
    """
    Accepted draws where has_conflict=1 — sources disagree on the canonical number.

    Distinguishes active conflicts (non-anomaly conflict observations still present)
    from stale conflicts (has_conflict=1 but all conflicting observations are now
    marked 'anomaly' — the GA lotteryusa cleanup pattern). Stale conflicts are
    informational and do NOT fail the check; they are candidates for has_conflict=0
    repair via POST /admin/repair/clear-stale-has-conflict.
    """
    w, p = _state_game_where(state, game)
    sep = " AND" if w else "WHERE"
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT d.canonical_key, d.state, d.game_type, d.draw_date, d.draw_time,
               d.winning_number, d.accepted_from_source, d.accepted_source_priority,
               d.observation_count, d.is_verified,
               -- Active conflict observations (non-anomaly)
               GROUP_CONCAT(
                   CASE WHEN o.reconciliation_status = 'conflict'
                        THEN o.source_name || ':' || o.winning_number END,
                   ' | ') AS active_conflicting_claims,
               -- Anomaly observations that were the original conflict source
               GROUP_CONCAT(
                   CASE WHEN o.reconciliation_status = 'anomaly'
                        THEN o.source_name || ':' || o.winning_number END,
                   ' | ') AS anomaly_claims,
               COUNT(CASE WHEN o.reconciliation_status = 'conflict' THEN 1 END)
                   AS active_conflict_count
        FROM draws d
        LEFT JOIN draw_observations o
            ON d.canonical_key = o.canonical_key
            AND o.reconciliation_status IN ('conflict', 'anomaly')
        {w} {sep} d.has_conflict = 1
        GROUP BY d.canonical_key
        ORDER BY d.state, d.game_type, d.draw_date
        """, p).fetchall())

    active_rows = []
    stale_rows = []
    for r in rows:
        if (r.get("active_conflict_count") or 0) > 0:
            r["is_stale_conflict"] = False
            active_rows.append(r)
        else:
            r["is_stale_conflict"] = True
            stale_rows.append(r)

    stale_note = (f" {len(stale_rows)} stale (all anomaly) — "
                  "safe to clear via /admin/repair/clear-stale-has-conflict."
                  if stale_rows else "")

    return CheckResult(
        check_id=7,
        name="accepted_draws_with_conflict",
        severity=SEVERITY_HIGH,
        row_count=len(rows),
        rows=rows,
        description=(
            f"Draw is marked has_conflict=1. {len(active_rows)} active conflict(s) "
            f"(non-anomaly sources disagree on winning number).{stale_note}"
        ),
        ok=len(active_rows) == 0,
    )


def check_8_observation_bad_status(conn, state, game) -> CheckResult:
    """Observations in conflict/anomaly/error states — grouped for review."""
    w, p = _state_game_where(state, game)
    sep = " AND" if w else "WHERE"
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT state, game_type, draw_time, source_name,
               reconciliation_status,
               COUNT(*)        AS count,
               MIN(draw_date)  AS earliest,
               MAX(draw_date)  AS latest,
               GROUP_CONCAT(DISTINCT conflict_note) AS sample_notes
        FROM draw_observations {w}
        {sep} reconciliation_status IN ('conflict', 'anomaly', 'error')
        GROUP BY state, game_type, draw_time, source_name, reconciliation_status
        ORDER BY reconciliation_status, state, game_type
        """, p).fetchall())
    return CheckResult(
        check_id=8,
        name="observation_bad_status_clusters",
        severity=SEVERITY_MEDIUM,
        row_count=len(rows),
        rows=rows,
        description=(
            "draw_observations in conflict/anomaly/error reconciliation states, "
            "grouped by state/game/draw_time/source for cluster analysis."
        ),
        ok=len(rows) == 0,
    )


def check_9_multiple_winning_numbers_per_key(conn, state, game) -> CheckResult:
    """
    canonical_key groups with more than one distinct winning_number across active observations.
    Excludes reconciliation_status='anomaly' rows — these are archived evidence and have
    already been resolved. Only non-anomaly observations are counted for CRITICAL detection.
    """
    w, p = _state_game_where(state, game)
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT o.canonical_key, o.state, o.game_type, o.draw_date, o.draw_time,
               COUNT(DISTINCT o.winning_number) AS distinct_numbers,
               GROUP_CONCAT(DISTINCT o.winning_number ORDER BY o.winning_number) AS all_numbers,
               GROUP_CONCAT(DISTINCT o.source_name ORDER BY o.source_name)       AS sources,
               d.winning_number AS accepted_number,
               d.accepted_from_source
        FROM draw_observations o
        LEFT JOIN draws d ON o.canonical_key = d.canonical_key
        {w}
        {"AND" if w else "WHERE"} o.reconciliation_status != 'anomaly'
        GROUP BY o.canonical_key
        HAVING distinct_numbers > 1
        ORDER BY o.state, o.game_type, o.draw_date
        """, p).fetchall())
    return CheckResult(
        check_id=9,
        name="multiple_winning_numbers_per_canonical_key",
        severity=SEVERITY_CRITICAL,
        row_count=len(rows),
        rows=rows,
        description=(
            "Two or more distinct winning numbers from non-anomaly observations for the same canonical_key. "
            "Only one can be correct. The accepted row may be wrong. "
            "(Anomaly observations are excluded — they are archived resolved evidence.)"
        ),
        ok=len(rows) == 0,
    )


def check_10_accepted_coverage_no_draw(conn, state, game) -> CheckResult:
    """scrape_coverage says accepted but the draws table has no row for that slot."""
    w, p = _state_game_where(state, game, prefix="sc")
    sep = " AND" if w else "WHERE"
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT sc.state, sc.game_type, sc.draw_date, sc.draw_time,
               sc.coverage_status, sc.observation_count, sc.last_source,
               sc.last_attempted_at, sc.notes
        FROM scrape_coverage sc
        LEFT JOIN draws d
            ON sc.state = d.state
            AND sc.game_type = d.game_type
            AND sc.draw_date = d.draw_date
            AND sc.draw_time = d.draw_time
        {w} {sep} sc.coverage_status = 'accepted'
          AND d.canonical_key IS NULL
        ORDER BY sc.state, sc.game_type, sc.draw_date
        """, p).fetchall())
    return CheckResult(
        check_id=10,
        name="accepted_coverage_but_no_draw_row",
        severity=SEVERITY_HIGH,
        row_count=len(rows),
        rows=rows,
        description=(
            "scrape_coverage.coverage_status = 'accepted' but no corresponding row "
            "exists in draws. Coverage claims completeness that doesn't exist."
        ),
        ok=len(rows) == 0,
    )


def check_11_draw_missing_accepted_coverage(conn, state, game) -> CheckResult:
    """Draw row exists but scrape_coverage is missing or not marked accepted."""
    w, p = _state_game_where(state, game, prefix="d")
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT d.canonical_key, d.state, d.game_type, d.draw_date, d.draw_time,
               d.winning_number, d.accepted_from_source,
               COALESCE(sc.coverage_status, 'MISSING') AS coverage_status,
               sc.last_source, sc.last_attempted_at
        FROM draws d
        LEFT JOIN scrape_coverage sc
            ON d.state = sc.state
            AND d.game_type = sc.game_type
            AND d.draw_date = sc.draw_date
            AND d.draw_time = sc.draw_time
        {w}
        {"AND" if w else "WHERE"} (sc.id IS NULL OR sc.coverage_status != 'accepted')
        ORDER BY d.state, d.game_type, d.draw_date
        """, p).fetchall())
    return CheckResult(
        check_id=11,
        name="draw_row_without_accepted_coverage",
        severity=SEVERITY_MEDIUM,
        row_count=len(rows),
        rows=rows,
        description=(
            "A draw row exists but scrape_coverage is missing or not 'accepted'. "
            "Coverage tracking is inconsistent with the draws table."
        ),
        ok=len(rows) == 0,
    )


def check_12_latest_coverage_by_state_game_drawtime(conn, state, game) -> CheckResult:
    """Latest accepted draw_date by state/game/draw_time/source — staleness indicator."""
    w, p = _state_game_where(state, game)
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT state, game_type, draw_time, accepted_from_source,
               COUNT(*)        AS total_draws,
               MIN(draw_date)  AS earliest_draw,
               MAX(draw_date)  AS latest_draw,
               JULIANDAY('now') - JULIANDAY(MAX(draw_date)) AS days_since_latest
        FROM draws {w}
        GROUP BY state, game_type, draw_time, accepted_from_source
        ORDER BY state, game_type, draw_time, accepted_from_source
        """, p).fetchall())

    stale = [r for r in rows if r.get("days_since_latest") is not None and r["days_since_latest"] > 7]
    return CheckResult(
        check_id=12,
        name="latest_coverage_by_state_game_drawtime",
        severity=SEVERITY_LOW,
        row_count=len(rows),
        rows=rows,
        description=(
            f"Latest accepted draw per state/game/draw_time/source. "
            f"{len(stale)} slot(s) have not been updated in >7 days."
        ),
        ok=len(stale) == 0,
    )


def check_13_source_reliability(conn, state, game) -> CheckResult:
    """Source reliability: raw counts, accepted, conflict, anomaly, date range per source."""
    w, p = _state_game_where(state, game)
    rows = rows_to_dicts(conn.execute(
        f"""
        SELECT state, game_type, source_name,
               COUNT(*)                                                    AS total_observations,
               SUM(CASE WHEN reconciliation_status='accepted'  THEN 1 ELSE 0 END) AS accepted,
               SUM(CASE WHEN reconciliation_status='duplicate' THEN 1 ELSE 0 END) AS duplicate,
               SUM(CASE WHEN reconciliation_status='conflict'  THEN 1 ELSE 0 END) AS conflict,
               SUM(CASE WHEN reconciliation_status='anomaly'   THEN 1 ELSE 0 END) AS anomaly,
               SUM(CASE WHEN reconciliation_status='pending'   THEN 1 ELSE 0 END) AS pending,
               MIN(draw_date)  AS earliest_date,
               MAX(draw_date)  AS latest_date,
               ROUND(100.0 * SUM(CASE WHEN reconciliation_status='conflict' THEN 1 ELSE 0 END)
                     / COUNT(*), 2) AS conflict_pct,
               ROUND(100.0 * SUM(CASE WHEN reconciliation_status='anomaly' THEN 1 ELSE 0 END)
                     / COUNT(*), 2) AS anomaly_pct
        FROM draw_observations {w}
        GROUP BY state, game_type, source_name
        ORDER BY state, game_type, conflict_pct DESC
        """, p).fetchall())

    high_anomaly = [r for r in rows if (r.get("anomaly_pct") or 0) > 5]
    return CheckResult(
        check_id=13,
        name="source_reliability_summary",
        severity=SEVERITY_LOW,
        row_count=len(rows),
        rows=rows,
        description=(
            f"Source reliability by state/game. "
            f"{len(high_anomaly)} source(s) have anomaly_pct > 5%."
        ),
        ok=len(high_anomaly) == 0,
    )


def check_14_recent_coverage_gaps(conn, state, game, recent_days: int) -> CheckResult:
    """Recent coverage gaps: expected slots with no accepted draw in the last N days."""
    cutoff = (date.today() - timedelta(days=recent_days)).isoformat()

    # Derive active (state, game_type, draw_time) combos from draws that have data
    w, p = _state_game_where(state, game)
    active_combos = conn.execute(
        f"""
        SELECT DISTINCT state, game_type, draw_time
        FROM draws {w}
        ORDER BY state, game_type, draw_time
        """, p).fetchall()

    if not active_combos:
        return CheckResult(
            check_id=14,
            name="recent_coverage_gaps",
            severity=SEVERITY_MEDIUM,
            row_count=0,
            description=f"No active state/game/draw_time combos found.",
            ok=True,
        )

    gap_rows = []
    for combo in active_combos:
        st, gt, dt = combo["state"], combo["game_type"], combo["draw_time"]
        # For each day in the recent window, check whether we have a draw
        # Use scrape_coverage as the ground truth (it tracks both accepted and errors)
        missing = rows_to_dicts(conn.execute(
            """
            SELECT sc.state, sc.game_type, sc.draw_date, sc.draw_time,
                   COALESCE(sc.coverage_status, 'not_in_coverage') AS coverage_status,
                   sc.last_source, sc.last_attempted_at, sc.notes,
                   d.winning_number AS accepted_number
            FROM scrape_coverage sc
            LEFT JOIN draws d
                ON sc.state=d.state AND sc.game_type=d.game_type
                AND sc.draw_date=d.draw_date AND sc.draw_time=d.draw_time
            WHERE sc.state=? AND sc.game_type=? AND sc.draw_time=?
              AND sc.draw_date >= ?
              AND sc.coverage_status != 'accepted'
            ORDER BY sc.draw_date
            """, (st, gt, dt, cutoff)).fetchall())
        gap_rows.extend(missing)

    return CheckResult(
        check_id=14,
        name="recent_coverage_gaps",
        severity=SEVERITY_MEDIUM,
        row_count=len(gap_rows),
        rows=gap_rows,
        description=(
            f"Coverage slots in the last {recent_days} days (since {cutoff}) "
            f"that are not marked 'accepted'. Includes scrape_error, anomaly, not_scraped."
        ),
        ok=len(gap_rows) == 0,
    )


def check_15_suspicious_all_drawtime_duplication(conn, state, game) -> CheckResult:
    """
    Detect rows in draws where the same winning_number and source appears
    in all draw_times for the same state/game/date — the GA lotteryusa pattern.
    """
    w, p = _state_game_where(state, game)
    # First find how many draw_times each state/game uses
    dt_counts = {
        (r["state"], r["game_type"]): r["dt_count"]
        for r in rows_to_dicts(conn.execute(
            f"""
            SELECT state, game_type, COUNT(DISTINCT draw_time) AS dt_count
            FROM draws {w}
            GROUP BY state, game_type
            """, p).fetchall())
    }

    # Now look for same winning_number+source on same date spanning all draw_times
    all_rows = rows_to_dicts(conn.execute(
        f"""
        SELECT state, game_type, draw_date, accepted_from_source, winning_number,
               COUNT(DISTINCT draw_time)                           AS occupied_draw_times,
               GROUP_CONCAT(DISTINCT draw_time ORDER BY draw_time) AS draw_times
        FROM draws {w}
        GROUP BY state, game_type, draw_date, accepted_from_source, winning_number
        HAVING COUNT(DISTINCT draw_time) >= 2
        ORDER BY state, game_type, draw_date
        """, p).fetchall())

    # Flag rows where occupied_draw_times == total draw_times for that state/game
    suspicious = []
    for r in all_rows:
        key = (r["state"], r["game_type"])
        total_dts = dt_counts.get(key, 1)
        if r["occupied_draw_times"] >= total_dts:
            r["total_draw_times_for_game"] = total_dts
            r["is_full_sweep"] = True
            suspicious.append(r)
        elif r["occupied_draw_times"] >= 2:
            r["total_draw_times_for_game"] = total_dts
            r["is_full_sweep"] = False
            suspicious.append(r)

    return CheckResult(
        check_id=15,
        name="suspicious_all_drawtime_duplication_in_draws",
        severity=SEVERITY_CRITICAL,
        row_count=len(suspicious),
        rows=suspicious,
        description=(
            "Same winning_number from the same source appears in 2+ accepted draws "
            "for different draw_times on the same date. Full-sweep rows (covering ALL "
            "draw_times) are the GA lotteryusa pattern of fabricated draws."
        ),
        ok=len([r for r in suspicious if r.get("is_full_sweep")]) == 0,
    )


# ---------------------------------------------------------------------------
# Repair queue candidates aggregator
# ---------------------------------------------------------------------------

def build_repair_queue(checks: list[CheckResult]) -> list[dict]:
    """
    Combine CRITICAL and HIGH findings into a single repair_queue list,
    tagged with which check they came from.
    """
    queue = []
    for c in checks:
        if c.ok or c.severity not in (SEVERITY_CRITICAL, SEVERITY_HIGH):
            continue
        for row in c.rows:
            entry = {"audit_check_id": c.check_id, "audit_check_name": c.name,
                     "severity": c.severity}
            entry.update(row)
            queue.append(entry)
    return queue


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        path.write_text("# no rows\n", encoding="utf-8")
        return
    # Build union of all keys (preserving first-seen order) so merged CSVs
    # with different column sets don't crash the DictWriter.
    seen: dict[str, None] = {}
    for row in rows:
        seen.update({k: None for k in row})
    fieldnames = list(seen.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore",
                           restval="")
        w.writeheader()
        w.writerows(rows)


def write_json_summary(summary: AuditSummary, path: Path) -> None:
    doc = {
        "db_path":      summary.db_path,
        "run_at":       summary.run_at,
        "state_filter": summary.state_filter,
        "game_filter":  summary.game_filter,
        "recent_days":  summary.recent_days,
        "overall_ok":   summary.overall_ok,
        "counts": {
            "critical": summary.critical_count,
            "high":     summary.high_count,
            "medium":   summary.medium_count,
            "low":      summary.low_count,
        },
        "checks": [c.to_summary_dict() for c in summary.checks],
    }
    path.write_text(json.dumps(doc, indent=2, default=str), encoding="utf-8")


def write_markdown_summary(summary: AuditSummary, path: Path) -> None:
    lines = [
        "# Database Integrity Audit",
        "",
        f"**DB path:** `{summary.db_path}`  ",
        f"**Run at:** {summary.run_at}  ",
        f"**Filters:** state={summary.state_filter or 'all'}, "
        f"game={summary.game_filter or 'all'}, "
        f"recent_days={summary.recent_days}",
        "",
        "## Overall Status",
        "",
    ]
    status_icon = "✅ PASS" if summary.overall_ok else "❌ FAIL"
    lines += [
        f"**{status_icon}**",
        "",
        f"| Severity | Issues |",
        f"|----------|--------|",
        f"| CRITICAL | {summary.critical_count} |",
        f"| HIGH     | {summary.high_count} |",
        f"| MEDIUM   | {summary.medium_count} |",
        f"| LOW      | {summary.low_count} |",
        "",
        "## Check Results",
        "",
        "| # | Name | Severity | Status | Row Count | Description |",
        "|---|------|----------|--------|-----------|-------------|",
    ]
    for c in summary.checks:
        icon = "✅" if c.ok else ("🔴" if c.severity == SEVERITY_CRITICAL
                                  else "🟠" if c.severity == SEVERITY_HIGH
                                  else "🟡" if c.severity == SEVERITY_MEDIUM else "🔵")
        lines.append(
            f"| {c.check_id} | {c.name} | {c.severity} | {icon} | {c.row_count} | {c.description} |"
        )

    lines += [
        "",
        "## Interpretation Guide",
        "",
        "> **Rule: incomplete coverage is safer than false verified coverage.**  ",
        "> A missing draw slot is recoverable. A fabricated draw corrupts backtest hit counts permanently.",
        "",
        "- **CRITICAL**: Stop. Fix before running any backtest.",
        "- **HIGH**: Fix before using affected state/game in production.",
        "- **MEDIUM**: Track. Missing coverage is expected during catchup.",
        "- **LOW**: Informational. Review periodically.",
        "",
        "See `docs/database_integrity_audit.md` for full documentation.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main audit runner
# ---------------------------------------------------------------------------

def run_audit(
    db_path:     str,
    out_dir:     Path,
    state:       str | None = None,
    game:        str | None = None,
    recent_days: int = 45,
    fmt:         str = "all",
) -> AuditSummary:
    from datetime import datetime, timezone
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info("Opening DB (read-only): %s", db_path)
    conn = open_readonly(db_path)

    summary = AuditSummary(
        db_path=db_path,
        run_at=run_at,
        state_filter=state,
        game_filter=game,
        recent_days=recent_days,
    )

    checks_to_run = [
        lambda: check_1_duplicate_canonical_keys(conn, state, game),
        lambda: check_2_same_number_across_draw_times_observations(conn, state, game),
        lambda: check_3_invalid_draw_times(conn, state, game),
        lambda: check_4_pick3_digit_length(conn, state, game),
        lambda: check_5_pick4_digit_length(conn, state, game),
        lambda: check_6_leading_zero_risk(conn, state, game),
        lambda: check_7_accepted_with_conflict(conn, state, game),
        lambda: check_8_observation_bad_status(conn, state, game),
        lambda: check_9_multiple_winning_numbers_per_key(conn, state, game),
        lambda: check_10_accepted_coverage_no_draw(conn, state, game),
        lambda: check_11_draw_missing_accepted_coverage(conn, state, game),
        lambda: check_12_latest_coverage_by_state_game_drawtime(conn, state, game),
        lambda: check_13_source_reliability(conn, state, game),
        lambda: check_14_recent_coverage_gaps(conn, state, game, recent_days),
        lambda: check_15_suspicious_all_drawtime_duplication(conn, state, game),
    ]

    for fn in checks_to_run:
        try:
            result = fn()
            summary.checks.append(result)
            icon = "✅" if result.ok else f"❌ {result.row_count} rows"
            logger.info("  Check %2d %-50s %s", result.check_id, result.name, icon)
        except Exception as e:
            logger.error("  Check failed with exception: %s", e, exc_info=True)

    conn.close()

    _ensure_dir(out_dir)
    _write_outputs(summary, out_dir, fmt)

    return summary


def _write_outputs(summary: AuditSummary, out_dir: Path, fmt: str) -> None:
    do_json = fmt in ("json", "all")
    do_csv  = fmt in ("csv", "all")
    do_md   = fmt in ("markdown", "all")

    check_map = {c.check_id: c for c in summary.checks}

    if do_json:
        write_json_summary(summary, out_dir / "audit_summary.json")
        logger.info("  Wrote audit_summary.json")

    if do_md:
        write_markdown_summary(summary, out_dir / "audit_summary.md")
        logger.info("  Wrote audit_summary.md")

    if do_csv:
        # duplicate_drawtime_groups.csv — checks 2 + 15
        c2 = check_map.get(2)
        c15 = check_map.get(15)
        dup_rows = (c2.rows if c2 else []) + (c15.rows if c15 else [])
        write_csv(dup_rows, out_dir / "duplicate_drawtime_groups.csv")

        # digit_length_issues.csv — checks 4 + 5
        digit_rows = (check_map[4].rows if 4 in check_map else []) + \
                     (check_map[5].rows if 5 in check_map else [])
        write_csv(digit_rows, out_dir / "digit_length_issues.csv")

        # leading_zero_risk.csv — check 6
        write_csv(check_map[6].rows if 6 in check_map else [],
                  out_dir / "leading_zero_risk.csv")

        # conflict_rows.csv — active conflicts only (checks 7 active + 9)
        c7_rows = check_map[7].rows if 7 in check_map else []
        active_c7 = [r for r in c7_rows if not r.get("is_stale_conflict")]
        conflict_rows = active_c7 + (check_map[9].rows if 9 in check_map else [])
        write_csv(conflict_rows, out_dir / "conflict_rows.csv")

        # stale_conflict_candidates.csv — has_conflict=1 but all conflict obs are anomaly
        stale_c7 = [r for r in c7_rows if r.get("is_stale_conflict")]
        write_csv(stale_c7, out_dir / "stale_conflict_candidates.csv")

        # coverage_mismatches.csv — checks 10 + 11
        cov_rows = (check_map[10].rows if 10 in check_map else []) + \
                   (check_map[11].rows if 11 in check_map else [])
        write_csv(cov_rows, out_dir / "coverage_mismatches.csv")

        # latest_coverage_by_state_game_drawtime.csv — check 12
        write_csv(check_map[12].rows if 12 in check_map else [],
                  out_dir / "latest_coverage_by_state_game_drawtime.csv")

        # source_reliability.csv — check 13
        write_csv(check_map[13].rows if 13 in check_map else [],
                  out_dir / "source_reliability.csv")

        # recent_coverage_gaps.csv — check 14
        write_csv(check_map[14].rows if 14 in check_map else [],
                  out_dir / "recent_coverage_gaps.csv")

        # repair_queue_candidates.csv — all CRITICAL + HIGH failures
        repair_queue = build_repair_queue(summary.checks)
        write_csv(repair_queue, out_dir / "repair_queue_candidates.csv")

        # observation_bad_status_clusters.csv — check 8 (distinct from conflict_rows)
        write_csv(check_map[8].rows if 8 in check_map else [],
                  out_dir / "observation_bad_status_clusters.csv")

        logger.info("  Wrote CSV files to %s", out_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    default_db = os.environ.get(
        "LOTTERY_DB_PATH",
        str(Path(__file__).parent.parent / "data" / "history_all_states.db"),
    )
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--db-path",     default=default_db,
                   help="Path to SQLite database (default: $LOTTERY_DB_PATH or data/history_all_states.db)")
    p.add_argument("--out-dir",     default=None,
                   help="Output directory (default: outputs/audits/<timestamp>)")
    p.add_argument("--state",       default=None, help="Filter to one state, e.g. GA")
    p.add_argument("--game",        default=None, help="Filter to one game: pick3 | pick4")
    p.add_argument("--recent-days", type=int, default=45,
                   help="Lookback window for recent coverage gap check (default: 45)")
    p.add_argument("--format",      default="all",
                   choices=["json", "csv", "markdown", "all"],
                   help="Output format (default: all)")
    p.add_argument("--log-level",   default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args()


def main() -> int:
    from datetime import datetime
    args = _parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    db_path = Path(args.db_path)
    if not db_path.exists():
        logger.error("Database not found: %s", db_path)
        logger.error("Set LOTTERY_DB_PATH or pass --db-path.")
        return 1

    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("outputs") / "audits" / ts

    logger.info("=" * 60)
    logger.info("Lottery DB Integrity Audit")
    logger.info("DB:          %s", db_path)
    logger.info("Output:      %s", out_dir)
    logger.info("State:       %s", args.state or "all")
    logger.info("Game:        %s", args.game or "all")
    logger.info("Recent days: %d", args.recent_days)
    logger.info("Format:      %s", args.format)
    logger.info("=" * 60)

    summary = run_audit(
        db_path=str(db_path),
        out_dir=out_dir,
        state=args.state,
        game=args.game,
        recent_days=args.recent_days,
        fmt=args.format,
    )

    print()
    print("=" * 60)
    print("AUDIT COMPLETE")
    print(f"  Output dir:  {out_dir}")
    print(f"  CRITICAL:    {summary.critical_count}")
    print(f"  HIGH:        {summary.high_count}")
    print(f"  MEDIUM:      {summary.medium_count}")
    print(f"  LOW:         {summary.low_count}")
    print(f"  Overall:     {'PASS' if summary.overall_ok else 'FAIL'}")
    print("=" * 60)

    if not summary.overall_ok:
        print()
        print("Issues requiring attention:")
        for c in summary.checks:
            if not c.ok and c.severity in (SEVERITY_CRITICAL, SEVERITY_HIGH):
                print(f"  [{c.severity}] Check {c.check_id}: {c.name} — {c.row_count} row(s)")
        print()
        print("See repair_queue_candidates.csv for actionable rows.")

    # Exit code: 2 = critical issues, 1 = high issues, 0 = pass
    if summary.critical_count > 0:
        return 2
    if summary.high_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
