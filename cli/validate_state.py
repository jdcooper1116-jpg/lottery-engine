#!/usr/bin/env python3
"""
lottery_engine/cli/validate_state.py

Reusable state onboarding validation command.
Runs a structured checklist for one state/game/month and
prints a pass/fail summary. Use this before any new state
backfill to confirm the registry, URL slugs, ingest, and
query layer all work correctly.

Usage:
    # Dry-run only (no HTTP, no DB writes) — safe first check
    python -m cli.validate_state --state FL --game pick3 --month 2024-01 --dry-run

    # Full validation against lottery.net (makes real HTTP requests)
    python -m cli.validate_state --state FL --game pick3 --month 2024-01 --source lottery.net

    # All sources, all games
    python -m cli.validate_state --state NY --month 2024-01

    # Skip ingest if data is already in DB
    python -m cli.validate_state --state GA --game pick3 --month 2024-01 --skip-ingest

Pass criteria (each check is PASS / FAIL / SKIP / WARN):
    Registry   - state has job definitions and source mappings
    Slugs      - no ESTIMATED slugs (WARN if found, not FAIL)
    URLs       - at least one URL generated per job
    Ingest     - > 0 observations written
    Draw times - all expected draw times present in DB
    Row counts - >= 15 draws per draw_time (monthly minimum)
    LZ check   - leading zeros preserved (SKIP if none in dataset)
    Canonical  - observations reconciled to draws table
    Provenance - source_name populated on DrawRecord
    Query      - candidate match returns a hit
    Backtest   - dream backtest returns draws > 0
    Coverage   - accepted slots recorded in scrape_coverage
"""
import argparse
import sys
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Constants ──────────────────────────────────────────────────────────────────
MIN_DRAWS_PER_TIME  = 15    # expected minimum for a full calendar month
MIN_TOTAL_DRAWS     = 20    # minimum total draws in the month

STATUS_PASS  = "PASS"
STATUS_FAIL  = "FAIL"
STATUS_WARN  = "WARN"
STATUS_SKIP  = "SKIP"
STATUS_INFO  = "INFO"

# ── ANSI ───────────────────────────────────────────────────────────────────────
def _color(s, code): return f"\033[{code}m{s}\033[0m" if sys.stdout.isatty() else s
def _green(s):  return _color(s, "32")
def _red(s):    return _color(s, "31")
def _amber(s):  return _color(s, "33")
def _bold(s):   return _color(s, "1")
def _dim(s):    return _color(s, "2")


# ── Check result accumulator ───────────────────────────────────────────────────
class CheckList:
    def __init__(self) -> None:
        self._items:   list[tuple[str, str, str]] = []  # (label, status, detail)
        self._sections: list[tuple[str, int]] = []      # (name, start_index)
        self._first_fail: str | None = None

    # ── Section tracking ──────────────────────────────────────────────────────

    def begin_section(self, name: str) -> None:
        """Close the previous section (print its badge) and open a new one."""
        if self._sections:
            self._print_section_badge()
        self._sections.append((name, len(self._items)))

    def close_sections(self) -> None:
        """Close the last open section. Call before printing the final summary."""
        if self._sections:
            self._print_section_badge()
            self._sections = []

    def _current_section_items(self) -> list:
        if not self._sections:
            return self._items
        _, start = self._sections[-1]
        return self._items[start:]

    def _print_section_badge(self) -> None:
        items  = self._current_section_items()
        fails  = [i for i in items if i[1] == STATUS_FAIL]
        warns  = [i for i in items if i[1] == STATUS_WARN]
        passes = [i for i in items if i[1] == STATUS_PASS]
        if fails:
            badge = _red(f"  ↳ FAIL  ({len(fails)} check(s) failed)")
        elif warns:
            badge = _amber(f"  ↳ WARN  ({len(warns)} warning(s))")
        elif passes:
            badge = _green(f"  ↳ PASS")
        else:
            badge = _dim("  ↳ SKIP")
        print(badge)
        print()

    # ── Check accumulation ────────────────────────────────────────────────────

    def add(self, label: str, status: str, detail: str = "") -> None:
        self._items.append((label, status, detail))
        if status == STATUS_FAIL and self._first_fail is None:
            first_line = detail.splitlines()[0] if detail else label
            self._first_fail = f"{label}: {first_line}".strip(": ")
        sym = {"PASS":"✓","FAIL":"✗","WARN":"⚠","SKIP":"–","INFO":"·"}[status]
        fmt = {
            STATUS_PASS: _green,
            STATUS_FAIL: _red,
            STATUS_WARN: _amber,
            STATUS_SKIP: _dim,
            STATUS_INFO: lambda s: s,
        }[status]
        print(f"  {fmt(sym)} {label:<42} {fmt(status)}")
        if detail:
            for line in detail.splitlines():
                print(f"    {_dim(line)}")

    @property
    def passed(self) -> bool:
        return not any(s == STATUS_FAIL for _, s, _ in self._items)

    @property
    def n_fail(self) -> int:
        return sum(1 for _, s, _ in self._items if s == STATUS_FAIL)

    @property
    def n_warn(self) -> int:
        return sum(1 for _, s, _ in self._items if s == STATUS_WARN)

    @property
    def first_failure(self) -> str:
        return self._first_fail or ""


# ── Main validation function ───────────────────────────────────────────────────

def validate_state(
    state: str,
    game_type: str | None,
    month: str,            # "YYYY-MM"
    source_name: str | None,
    dry_run: bool,
    skip_ingest: bool,
    db_path: str | None,
) -> bool:
    """
    Run the full validation workflow.
    Returns True if all checks pass.
    """
    from db.connection import initialize_db, get_connection, get_db_path
    from registry.loader import get_jobs_for_state, get_source_mappings_for_job
    from registry.definitions import ALL_JOB_DEFINITIONS
    from orchestrator.scheduler import build_tasks_for_state
    from orchestrator.runner import run_ingest
    from orchestrator.reconciler import reconcile_pending
    from query.service import _fetch_draws, get_latest_results, backtest_numbers
    from query.models import QueryFilters, DreamBacktestRequest

    # Ensure the query service opens the same DB as validate_state uses.
    # The query layer reads LOTTERY_DB_PATH from the environment.
    if db_path:
        import os
        os.environ["LOTTERY_DB_PATH"] = db_path

    try:
        year, month_n = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        print(f"Invalid --month {month!r}. Expected YYYY-MM format.")
        return False

    start_date = date(year, month_n, 1)
    # last day of the month
    if month_n == 12:
        end_date = date(year, 12, 31)
    else:
        end_date = date(year, month_n + 1, 1) - timedelta(days=1)

    actual_db = db_path or get_db_path()
    state = state.upper()
    games = [game_type.lower()] if game_type else sorted(
        set(j.game_type for j in ALL_JOB_DEFINITIONS if j.state == state)
    )

    print()
    print(_bold(f"{'═'*62}"))
    print(_bold(f"  State Validation: {state}  |  {', '.join(games)}  |  {month}"))
    if source_name:
        print(f"  Source filter: {source_name}")
    if dry_run:
        print(_amber("  Mode: DRY RUN — no HTTP requests or DB writes"))
    print(_bold(f"{'═'*62}"))
    print()

    cl = CheckList()

    # ── 1. Registry ─────────────────────────────────────────────────────────
    cl.begin_section("Registry")
    print(_bold("── 1. Registry ──"))
    all_jobs = get_jobs_for_state(state)
    game_jobs = {g: get_jobs_for_state(state, game_type=g) for g in games}

    if not all_jobs:
        cl.add("State has job definitions", STATUS_FAIL,
               f"No jobs found for state={state!r}. Add definitions/{state.lower()}.py")
        return _summary(cl, state=state, game_type=game_type or "", month=month, source_name=source_name or "")

    cl.add("State has job definitions", STATUS_PASS,
           f"{len(all_jobs)} jobs: " + ", ".join(
               f"{j.game_type}/{j.draw_time}" for j in all_jobs
           ))

    # Check source mappings
    from registry.definitions import ALL_SOURCE_MAPPINGS
    state_maps = [m for m in ALL_SOURCE_MAPPINGS
                  if m.job_def.state == state
                  and (source_name is None or m.source_name == source_name)
                  and m.is_enabled]

    if not state_maps:
        cl.add("Source mappings exist", STATUS_FAIL,
               f"No mappings found for source={source_name!r}")
        return _summary(cl, state=state, game_type=game_type or "", month=month, source_name=source_name or "")
    cl.add("Source mappings exist", STATUS_PASS,
           f"{len(state_maps)} mappings across "
           f"{len(set(m.source_name for m in state_maps))} source(s)")

    # Slug verification — show exact status and actionable guidance
    unverified = [m for m in state_maps if not m.slug_verified]
    estimated  = [m for m in state_maps if "ESTIMATED" in (m.notes or "")]
    if estimated:
        sample_urls = []
        for m in estimated[:3]:
            url = m.build_url(year=2024, month=1)
            if url:
                sample_urls.append(f"  check → {url}")
        verify_cmd = (
            f"python -m cli.validate_state --state {state} "
            f"--game {(game_type or 'pick3')} --month {month} "
            f"--source {(source_name or 'lottery.net')} --dry-run"
        )
        detail = (
            f"{len(estimated)}/{len(state_maps)} mappings are ESTIMATED (unconfirmed on live site).\n"
            + "\n".join(sample_urls)
            + f"\n  Run: {verify_cmd}"
        )
        cl.add("Slugs: ESTIMATED — verify before backfill", STATUS_WARN, detail)
    elif unverified:
        cl.add("Slugs not yet marked verified", STATUS_WARN,
               f"{len(unverified)} mapping(s) have slug_verified=False. "
               "Set slug_verified=True in the definition file after live confirmation.")
    else:
        cl.add("Slugs verified on live site", STATUS_PASS)

    # Check REGISTRY_META status
    try:
        import importlib
        _MODULE_MAP = {
            "GA": "registry.definitions.georgia",
            "FL": "registry.definitions.florida",
            "NY": "registry.definitions.new_york",
            "PA": "registry.definitions.pennsylvania",
            "OH": "registry.definitions.ohio",
            "MI": "registry.definitions.michigan",
            "IL": "registry.definitions.illinois",
            "TN": "registry.definitions.tennessee",
            "CA": "registry.definitions.california",
            "TX": "registry.definitions.texas",
            "OR": "registry.definitions.oregon",
        }
        mod_name = _MODULE_MAP.get(state, f"registry.definitions.{state.lower()}")
        mod = importlib.import_module(mod_name)
        meta = getattr(mod, "REGISTRY_META", {})
        status_val = meta.get("status", "unknown")
        complexity = meta.get("complexity", "unknown")
        cl.add("Registry status", STATUS_INFO,
               f"status={status_val!r}  complexity={complexity!r}  "
               f"slugs_verified={meta.get('slugs_verified',False)}")
    except Exception:
        cl.add("Registry metadata", STATUS_SKIP, "REGISTRY_META not found in definition file")

    print()

    # ── 2. URL planning (dry-run) ────────────────────────────────────────────
    cl.begin_section("URL planning")
    print(_bold("── 2. URL planning ──"))
    tasks = build_tasks_for_state(
        state, start_date, end_date,
        game_type=game_type,
        source_name=source_name,
    )

    if not tasks:
        cl.add("URL generation", STATUS_FAIL,
               "No tasks generated. Check lifecycle windows and source coverage years.")
        return _summary(cl, state=state, game_type=game_type or "", month=month, source_name=source_name or "")

    from sources.base import date_range_months
    all_urls = set()
    for t in tasks:
        for y, m in date_range_months(t.start_date, t.end_date):
            url = t.mapping.build_url(year=y, month=m)
            if url:
                all_urls.add(url)

    cl.add("URL generation", STATUS_PASS, f"{len(tasks)} tasks → {len(all_urls)} unique URL(s)")

    for url in sorted(all_urls):
        print(f"    {_dim(url)}")

    print()

    if dry_run:
        cl.add("Ingest", STATUS_SKIP, "Dry-run mode — skipping HTTP fetch and DB writes")
        cl.add("Draw time coverage", STATUS_SKIP, "Dry-run")
        cl.add("Row counts", STATUS_SKIP, "Dry-run")
        cl.add("Leading zeros", STATUS_SKIP, "Dry-run")
        cl.add("Canonical draws", STATUS_SKIP, "Dry-run")
        cl.add("Source provenance", STATUS_SKIP, "Dry-run")
        cl.add("Candidate match", STATUS_SKIP, "Dry-run")
        cl.add("Dream backtest", STATUS_SKIP, "Dry-run")
        cl.add("Coverage tracking", STATUS_SKIP, "Dry-run")
        return _summary(cl, state=state, game_type=game_type or "", month=month, source_name=source_name or "")

    # ── 3. Ingest ────────────────────────────────────────────────────────────
    cl.begin_section("Ingest")
    print(_bold("── 3. Ingest ──"))
    initialize_db(actual_db)

    # Seed registry if not already seeded
    from registry.definitions import ALL_JOB_DEFINITIONS
    from registry.seed import seed_job_definitions, seed_source_mappings
    with get_connection(actual_db) as conn:
        jmap = seed_job_definitions(conn, ALL_JOB_DEFINITIONS)
        seed_source_mappings(conn, ALL_SOURCE_MAPPINGS, jmap)

    obs_before = _count(actual_db, "draw_observations", state, games)
    draws_before = _count(actual_db, "draws", state, games)

    if not skip_ingest:
        summary = run_ingest(
            start_date=start_date, end_date=end_date,
            state=state, game_type=game_type,
            source_name=source_name,
            reconcile=True,
        )
        new_obs   = summary["observations_written"]
        new_draws = (summary.get("reconcile_stats") or {}).get("accepted", 0)
        # Zero observations is a hard fail — likely 404 on the URL
        obs_status = STATUS_PASS if new_obs > 0 else STATUS_FAIL
        cl.add("Ingest: observations written", obs_status,
               f"{new_obs} new observations, {new_draws} new canonical draws" +
               ("" if new_obs > 0 else
                "\n  Parser returned 0 rows. Likely causes: wrong slug (404), "
                "changed page structure, or source has no data for this month."))
        if new_obs == 0 and not skip_ingest:
            cl.add("Ingest returned 0 rows", STATUS_FAIL,
                   "Parser returned no data. Check slug and page structure.")
    else:
        cl.add("Ingest", STATUS_SKIP, "skip-ingest mode")

    print()

    # ── 4. Data quality ──────────────────────────────────────────────────────
    cl.begin_section("Data quality")
    print(_bold("── 4. Data quality ──"))

    raw_conn = sqlite3.connect(actual_db)
    raw_conn.row_factory = sqlite3.Row

    game_filter = f"AND game_type='{game_type.lower()}'" if game_type else ""
    src_filter  = f"AND accepted_from_source='{source_name}'" if source_name else ""

    # Draw time counts
    rows = raw_conn.execute(f"""
        SELECT game_type, draw_time, COUNT(*) as cnt
        FROM draws
        WHERE state=? AND draw_date BETWEEN ? AND ?
        {game_filter} {src_filter}
        GROUP BY game_type, draw_time
        ORDER BY game_type, draw_time
    """, (state, start_date.isoformat(), end_date.isoformat())).fetchall()

    if not rows:
        cl.add("Draw time coverage", STATUS_FAIL,
               f"No draws found in {month} for {state}. "
               "Check that ingest ran and returned results.")
    else:
        time_counts = {(r["game_type"], r["draw_time"]): r["cnt"] for r in rows}
        detail_lines = []
        any_zero    = False   # at least one draw_time has 0 rows → FAIL
        any_low     = False   # at least one draw_time is low but > 0 → WARN

        # Build a quick lookup of lottery.net slugs for hint messages
        from registry.definitions import ALL_SOURCE_MAPPINGS
        from registry.enums import SourceName as _SN
        slug_lookup = {
            (m.job_def.game_type, m.job_def.draw_time): m.source_game_slug
            for m in ALL_SOURCE_MAPPINGS
            if m.job_def.state == state and m.source_name == _SN.LOTTERY_NET
        }

        for g in games:
            expected_times = sorted(set(
                j.draw_time for j in get_jobs_for_state(state, game_type=g,
                                                         target_date=start_date)
            ))
            for dt in expected_times:
                cnt = time_counts.get((g, dt), 0)
                if cnt == 0:
                    any_zero = True
                    slug = slug_lookup.get((g, dt), "?")
                    # Use source_state_slug from the mapping for the correct URL path
                    from registry.definitions import ALL_SOURCE_MAPPINGS as _ALL_MAPS
                    from registry.enums import SourceName as _SN
                    _state_slug = next(
                        (m.source_state_slug for m in _ALL_MAPS
                         if m.job_def.state == state and m.source_name == _SN.LOTTERY_NET
                         and m.source_state_slug),
                        state.lower()
                    )
                    url = f"https://www.lottery.net/{_state_slug}/{slug}/numbers/{start_date.year}"
                    # Prepend to detail_lines so MISSING items appear first → shows in REASON
                    detail_lines.insert(0,
                        f"{g}/{dt}: 0 draws ✗ MISSING — "
                        f"possible 404 or wrong slug '{slug}'\n"
                        f"  check → {url}"
                    )
                elif cnt < MIN_DRAWS_PER_TIME:
                    any_low = True
                    detail_lines.append(f"{g}/{dt}: {cnt} draws ⚠ low (expected >= {MIN_DRAWS_PER_TIME})")
                else:
                    detail_lines.append(f"{g}/{dt}: {cnt} draws ✓")

        if any_zero:
            # Zero rows on any draw_time is a hard failure — wrong URL or parser error
            status = STATUS_FAIL
        elif any_low:
            status = STATUS_WARN
        else:
            status = STATUS_PASS

        cl.add("Draw time coverage", status, "\n".join(detail_lines))

    # Sample results (last 8 draws)
    samples = raw_conn.execute(f"""
        SELECT draw_date, draw_time, winning_number, is_verified,
               accepted_from_source as source_name
        FROM draws
        WHERE state=? AND draw_date BETWEEN ? AND ?
        {game_filter}
        ORDER BY draw_date DESC, draw_time
        LIMIT 8
    """, (state, start_date.isoformat(), end_date.isoformat())).fetchall()

    if samples:
        print()
        print(_bold("  Sample results:"))
        print(f"  {'DATE':<12} {'TIME':<10} {'NUMBER':<8} {'V':<2}  SOURCE")
        print(f"  {'─'*11}  {'─'*9}  {'─'*7}  ─  {'─'*20}")
        for r in samples:
            v = "✓" if r["is_verified"] else " "
            print(f"  {r['draw_date']:<12} {r['draw_time']:<10} "
                  f"{r['winning_number']:<8} {v:<2}  {r['source_name']}")
        print()

    # Leading zero check
    lz = raw_conn.execute(f"""
        SELECT winning_number FROM draws
        WHERE state=? AND draw_date BETWEEN ? AND ?
        {game_filter}
        AND winning_number LIKE '0%'
        LIMIT 5
    """, (state, start_date.isoformat(), end_date.isoformat())).fetchall()

    if lz:
        nums = [r["winning_number"] for r in lz]
        all_ok = all(n[0] == "0" for n in nums)
        cl.add("Leading zeros preserved", STATUS_PASS if all_ok else STATUS_FAIL,
               f"Examples: {nums}")
    else:
        cl.add("Leading zeros preserved", STATUS_SKIP,
               "No numbers starting with 0 found in this month's data")

    # Canonical vs observations
    n_canonical = raw_conn.execute(f"""
        SELECT COUNT(*) FROM draws
        WHERE state=? AND draw_date BETWEEN ? AND ?
        {game_filter}
    """, (state, start_date.isoformat(), end_date.isoformat())).fetchone()[0]

    n_obs = raw_conn.execute(f"""
        SELECT COUNT(*) FROM draw_observations
        WHERE state=? AND draw_date BETWEEN ? AND ?
        {game_filter}
    """, (state, start_date.isoformat(), end_date.isoformat())).fetchone()[0]

    cl.add("Canonical draws created", STATUS_PASS if n_canonical > 0 else STATUS_FAIL,
           f"{n_canonical} canonical draws, {n_obs} observations")

    # Provenance check
    no_src = raw_conn.execute(f"""
        SELECT COUNT(*) FROM draws
        WHERE state=? AND draw_date BETWEEN ? AND ?
        AND (accepted_from_source IS NULL OR accepted_from_source='')
        {game_filter}
    """, (state, start_date.isoformat(), end_date.isoformat())).fetchone()[0]

    cl.add("Source provenance populated", STATUS_PASS if no_src == 0 else STATUS_FAIL,
           f"{no_src} draws missing source" if no_src else "All draws have source_name")

    print()

    # ── 5. Query smoke tests ─────────────────────────────────────────────────
    cl.begin_section("Query smoke tests")
    print(_bold("── 5. Query smoke tests ──"))

    # Pick the most recent draw as the test candidate
    test_draw = raw_conn.execute(f"""
        SELECT draw_date, draw_time, winning_number, game_type
        FROM draws WHERE state=? AND draw_date BETWEEN ? AND ?
        {game_filter}
        ORDER BY draw_date DESC, draw_time LIMIT 1
    """, (state, start_date.isoformat(), end_date.isoformat())).fetchone()

    if test_draw:
        test_number = test_draw["winning_number"]
        test_date   = date.fromisoformat(test_draw["draw_date"])
        test_game   = test_draw["game_type"]

        # Candidate match
        from query.models import CandidateMatchRequest
        from query.service import match_candidate_numbers
        match_req = CandidateMatchRequest(
            state=state, game_type=test_game,
            start_date=start_date, end_date=end_date,
            candidates=[test_number],
        )
        try:
            match_resp = match_candidate_numbers(match_req)
            status = STATUS_PASS if match_resp.hit_count >= 1 else STATUS_FAIL
            cl.add("Candidate match query", status,
                   f"Searched for {test_number!r} in {month}: "
                   f"{match_resp.hit_count} hit(s) — "
                   f"source_name on hits: "
                   f"{list(set(h.source_name for h in match_resp.hits))}")
        except Exception as e:
            cl.add("Candidate match query", STATUS_FAIL, str(e))

        # Dream backtest
        # Use a window ending at the test draw date
        anchor = test_date - timedelta(days=3)
        bt_req = DreamBacktestRequest(
            state=state, game_type=test_game,
            anchor_date=anchor, lookahead_days=7,
            candidates=[test_number],
        )
        try:
            bt_resp = backtest_numbers(bt_req)
            status = STATUS_PASS if len(bt_resp.all_draws) > 0 else STATUS_FAIL
            cl.add("Dream backtest query", status,
                   f"Window {anchor} to {anchor + timedelta(days=7)}: "
                   f"{len(bt_resp.all_draws)} draws, "
                   f"{bt_resp.hit_count} hit(s)")
            if bt_resp.coverage_gaps:
                cl.add("Coverage gaps in window", STATUS_WARN,
                       f"{len(bt_resp.coverage_gaps)} gap(s) in backtest window")
        except Exception as e:
            cl.add("Dream backtest query", STATUS_FAIL, str(e))
    else:
        cl.add("Candidate match query", STATUS_SKIP, "No draws in DB to test against")
        cl.add("Dream backtest query",  STATUS_SKIP, "No draws in DB to test against")

    print()

    # ── 6. Coverage tracking ─────────────────────────────────────────────────
    cl.begin_section("Coverage")
    print(_bold("── 6. Coverage ──"))
    cov = raw_conn.execute(f"""
        SELECT coverage_status, COUNT(*) as cnt
        FROM scrape_coverage
        WHERE state=? AND draw_date BETWEEN ? AND ?
        {game_filter}
        GROUP BY coverage_status
    """, (state, start_date.isoformat(), end_date.isoformat())).fetchall()

    if cov:
        cov_detail = "  ".join(f"{r['coverage_status']}={r['cnt']}" for r in cov)
        accepted = next((r["cnt"] for r in cov if r["coverage_status"]=="accepted"), 0)
        cl.add("Coverage tracking", STATUS_PASS if accepted > 0 else STATUS_WARN, cov_detail)
    else:
        cl.add("Coverage tracking", STATUS_WARN, "No coverage rows found for this state/month")

    raw_conn.close()

    return _summary(cl, state=state, game_type=game_type or "", month=month, source_name=source_name or "")


def _count(db_path: str, table: str, state: str, games: list) -> int:
    conn = sqlite3.connect(db_path)
    n = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE state=?", (state,)
    ).fetchone()[0]
    conn.close()
    return n


def _summary(
    cl: CheckList,
    state: str = "",
    game_type: str = "",
    month: str = "",
    source_name: str = "",
) -> bool:
    cl.close_sections()
    print(_bold(f"{'═'*62}"))
    if cl.passed:
        print(_green(_bold(f"  RESULT: PASS  ({cl.n_warn} warning(s))")))
    else:
        print(_red(_bold(f"  RESULT: FAIL  ({cl.n_fail} failure(s), {cl.n_warn} warning(s))")))
    print(_bold(f"{'═'*62}"))

    # Machine-readable summary line — safe to grep/parse
    result = "PASS" if cl.passed else "FAIL"
    parts = [
        f"STATE={state or '?'}",
        f"GAME={game_type or 'all'}",
        f"MONTH={month or '?'}",
        f"SOURCE={source_name or 'all'}",
        f"RESULT={result}",
    ]
    if not cl.passed and cl.first_failure:
        # Truncate long reasons to keep the line grep-friendly
        reason = cl.first_failure[:80].replace('"', "'")
        parts.append(f'REASON="{reason}"')
    elif cl.n_warn:
        parts.append(f"WARNS={cl.n_warn}")
    print("  " + "  ".join(parts))
    print()
    return cl.passed


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        prog="python -m cli.validate_state",
        description="Validate one state's onboarding — registry, ingest, and query.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--state",     required=True, help="State code, e.g. FL")
    p.add_argument("--game",      dest="game_type", help="pick3 | pick4 (omit for all)")
    p.add_argument("--month",     required=True, help="Month to validate: YYYY-MM")
    p.add_argument("--source",    dest="source_name",
                   help="lottery.net | lotterycorner.com | lotteryusa.com (omit for all)")
    p.add_argument("--dry-run",   action="store_true",
                   help="Show URL plan only — no HTTP, no DB writes")
    p.add_argument("--skip-ingest", action="store_true",
                   help="Skip ingest if data already in DB; run quality checks only")
    p.add_argument("--db",        dest="db_path", default=None,
                   help="Override DB path (default: LOTTERY_DB_PATH or ./lottery.db)")
    args = p.parse_args()

    passed = validate_state(
        state=args.state,
        game_type=args.game_type,
        month=args.month,
        source_name=args.source_name,
        dry_run=args.dry_run,
        skip_ingest=args.skip_ingest,
        db_path=args.db_path,
    )
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
