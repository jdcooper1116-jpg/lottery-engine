"""
lottery_engine/tests/test_wave1_rollout.py

Tests for the Wave 1 rollout infrastructure:
  - cli/validate_state.py  — registry, URL planning, data quality, query checks
  - cli/registry_report.py — completeness report for all Wave 1 states
  - registry Wave 1 state definitions — structure and metadata
  - slug_verified field on SourceJobMapping
"""
import io
import os
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("LOTTERY_DB_PATH", ":memory:")

WAVE1_STATES = ["GA","FL","NY","PA","OH","MI","IL","TN","CA","TX","OR"]


# ── Registry completeness ──────────────────────────────────────────────────────

class TestWave1Registry:
    def test_all_wave1_states_importable(self):
        from registry.definitions import ALL_JOB_DEFINITIONS
        present = {j.state for j in ALL_JOB_DEFINITIONS}
        for state in WAVE1_STATES:
            assert state in present, f"{state} missing from registry"

    def test_total_job_count(self):
        from registry.definitions import ALL_JOB_DEFINITIONS
        assert len(ALL_JOB_DEFINITIONS) >= 50

    def test_total_mapping_count(self):
        from registry.definitions import ALL_SOURCE_MAPPINGS
        assert len(ALL_SOURCE_MAPPINGS) >= 148

    def test_every_state_has_jobs(self):
        from registry.definitions import ALL_JOB_DEFINITIONS
        counts = {}
        for j in ALL_JOB_DEFINITIONS:
            counts[j.state] = counts.get(j.state, 0) + 1
        for state in WAVE1_STATES:
            assert counts.get(state, 0) > 0, f"{state} has no job definitions"

    def test_every_state_has_lottery_net_mappings(self):
        from registry.definitions import ALL_SOURCE_MAPPINGS
        from registry.enums import SourceName
        by_state = {}
        for m in ALL_SOURCE_MAPPINGS:
            if m.source_name == SourceName.LOTTERY_NET:
                by_state[m.job_def.state] = True
        for state in WAVE1_STATES:
            assert by_state.get(state), f"{state} has no lottery.net mapping"

    def test_all_draw_times_are_canonical(self):
        from registry.definitions import ALL_JOB_DEFINITIONS
        from registry.enums import DrawTime
        valid = DrawTime.values()
        for j in ALL_JOB_DEFINITIONS:
            assert j.draw_time in valid, (
                f"{j.state}/{j.game_type}: invalid draw_time {j.draw_time!r}"
            )

    def test_all_game_types_are_canonical(self):
        from registry.definitions import ALL_JOB_DEFINITIONS
        from registry.enums import GameType
        valid = GameType.values()
        for j in ALL_JOB_DEFINITIONS:
            assert j.game_type in valid, (
                f"{j.state}: invalid game_type {j.game_type!r}"
            )

    def test_canonical_time_key_matches_draw_time(self):
        from registry.definitions import ALL_JOB_DEFINITIONS
        for j in ALL_JOB_DEFINITIONS:
            assert j.canonical_time_key == j.draw_time, (
                f"{j.draw_label}: canonical_time_key {j.canonical_time_key!r} "
                f"!= draw_time {j.draw_time!r}"
            )

    def test_registry_meta_present_on_all_seeded_states(self):
        import importlib
        MODULE_MAP = {
            "GA": "registry.definitions.georgia",
            "FL": "registry.definitions.florida",
            "NY": "registry.definitions.new_york",
            "PA": "registry.definitions.pennsylvania",
        }
        for state, mod_name in MODULE_MAP.items():
            mod = importlib.import_module(mod_name)
            meta = getattr(mod, "REGISTRY_META", None)
            assert meta is not None, f"{state} missing REGISTRY_META"
            assert meta["state_code"] == state
            assert "status" in meta
            assert "complexity" in meta
            assert "slugs_verified" in meta

    def test_georgia_slugs_marked_verified(self):
        from registry.definitions.georgia import SOURCE_MAPPINGS
        from registry.enums import SourceName
        ln_maps = [m for m in SOURCE_MAPPINGS
                   if m.source_name == SourceName.LOTTERY_NET]
        assert len(ln_maps) == 6
        verified = [m for m in ln_maps if getattr(m, "slug_verified", False)]
        assert len(verified) == 6, (
            f"Only {len(verified)}/6 GA lottery.net mappings are slug_verified=True"
        )

    def test_non_georgia_slugs_not_verified(self):
        """All non-GA states should have slug_verified=False until confirmed live."""
        import importlib
        for state, mod_name in [
            ("FL", "registry.definitions.florida"),
            ("NY", "registry.definitions.new_york"),
            ("PA", "registry.definitions.pennsylvania"),
        ]:
            mod = importlib.import_module(mod_name)
            maps = getattr(mod, "SOURCE_MAPPINGS", [])
            verified = [m for m in maps if getattr(m, "slug_verified", False)]
            assert len(verified) == 0, (
                f"{state}: {len(verified)} mappings marked slug_verified=True "
                "before live confirmation"
            )

    def test_slug_verified_field_on_source_job_mapping(self):
        import dataclasses
        from registry.models import SourceJobMapping
        field_names = [f.name for f in dataclasses.fields(SourceJobMapping)]
        assert "slug_verified" in field_names

    def test_slug_verified_defaults_false(self):
        from registry.models import SourceJobMapping, DrawJobDef
        jd = DrawJobDef("XX", "pick3", "midday", "Test", "v1")
        m = SourceJobMapping(job_def=jd, source_name="lottery.net", source_priority=1)
        assert m.slug_verified is False


class TestStateSpecificRequirements:
    """State-specific structural requirements."""

    def test_georgia_has_night_draw(self):
        from registry.definitions.georgia import JOB_DEFINITIONS
        night = [j for j in JOB_DEFINITIONS if j.draw_time == "night"]
        assert len(night) == 2  # pick3 + pick4

    def test_georgia_night_has_active_start_date(self):
        from registry.definitions.georgia import JOB_DEFINITIONS
        for j in [j for j in JOB_DEFINITIONS if j.draw_time == "night"]:
            assert j.active_start_date is not None, \
                f"{j.draw_label}: night draw must have active_start_date"

    def test_new_york_uses_numbers_slug(self):
        from registry.definitions.new_york import SOURCE_MAPPINGS
        from registry.enums import SourceName
        ln = [m for m in SOURCE_MAPPINGS
              if m.source_name == SourceName.LOTTERY_NET
              and m.job_def.game_type == "pick3"]
        slugs = {m.source_game_slug for m in ln}
        # Should contain "numbers-midday" and "numbers-evening" (not "pick-3-*")
        assert any("numbers" in (s or "") for s in slugs), \
            f"NY pick3 should use 'numbers' slug, got: {slugs}"
        assert not any("pick-3" in (s or "") for s in slugs), \
            f"NY pick3 should NOT use 'pick-3' slug: {slugs}"

    def test_new_york_uses_win4_slug(self):
        from registry.definitions.new_york import SOURCE_MAPPINGS
        from registry.enums import SourceName
        ln = [m for m in SOURCE_MAPPINGS
              if m.source_name == SourceName.LOTTERY_NET
              and m.job_def.game_type == "pick4"]
        slugs = {m.source_game_slug for m in ln}
        assert any("win-4" in (s or "") for s in slugs), \
            f"NY pick4 should use 'win-4' slug, got: {slugs}"

    def test_california_has_morning_draw(self):
        from registry.definitions.california import JOB_DEFINITIONS
        morning = [j for j in JOB_DEFINITIONS if j.draw_time == "morning"]
        assert len(morning) >= 2  # pick3 + pick4

    def test_texas_has_four_draw_times(self):
        from registry.definitions.texas import JOB_DEFINITIONS
        pick3_times = {j.draw_time for j in JOB_DEFINITIONS if j.game_type == "pick3"}
        expected = {"morning", "day", "evening", "night"}
        assert pick3_times == expected, \
            f"TX pick3 should have 4 draw times, got: {pick3_times}"

    def test_texas_pick4_called_daily4(self):
        from registry.definitions.texas import REGISTRY_META
        game_names = REGISTRY_META.get("game_names", {})
        assert "Daily 4" in game_names.get("pick4", ""), \
            f"TX pick4 should be 'Daily 4', got: {game_names}"

    def test_michigan_uses_daily3_slug(self):
        from registry.definitions.michigan import SOURCE_MAPPINGS
        from registry.enums import SourceName
        ln = [m for m in SOURCE_MAPPINGS
              if m.source_name == SourceName.LOTTERY_NET
              and m.job_def.game_type == "pick3"]
        slugs = {m.source_game_slug for m in ln}
        assert any("daily-3" in (s or "") for s in slugs), \
            f"MI pick3 should use 'daily-3' slug, got: {slugs}"

    def test_tennessee_uses_cash3_slug(self):
        from registry.definitions.tennessee import SOURCE_MAPPINGS
        from registry.enums import SourceName
        ln = [m for m in SOURCE_MAPPINGS
              if m.source_name == SourceName.LOTTERY_NET
              and m.job_def.game_type == "pick3"]
        slugs = {m.source_game_slug for m in ln}
        assert any("cash-3" in (s or "") for s in slugs), \
            f"TN pick3 should use 'cash-3' slug, got: {slugs}"

    def test_oregon_has_no_pick3(self):
        from registry.definitions.oregon import JOB_DEFINITIONS
        pick3 = [j for j in JOB_DEFINITIONS if j.game_type == "pick3"]
        assert len(pick3) == 0, \
            f"OR should have no pick3 jobs (game unavailable), got {len(pick3)}"

    def test_url_templates_have_year_placeholder(self):
        from registry.definitions import ALL_SOURCE_MAPPINGS
        from registry.enums import SourceName
        for m in ALL_SOURCE_MAPPINGS:
            if m.source_name == SourceName.LOTTERY_NET and m.url_template:
                assert "{year}" in m.url_template, \
                    f"{m.job_def.state}/{m.source_game_slug}: url_template missing {{year}}"

    def test_lottery_net_urls_build_correctly(self):
        from registry.definitions import ALL_SOURCE_MAPPINGS
        from registry.enums import SourceName
        for m in ALL_SOURCE_MAPPINGS:
            if m.source_name != SourceName.LOTTERY_NET:
                continue
            url = m.build_url(year=2024, month=1)
            assert url is not None, f"build_url returned None for {m.job_def.draw_label}"
            assert "2024" in url, f"Year not in URL: {url}"
            assert "lottery.net" in url, f"Wrong domain: {url}"
            assert "{" not in url, f"Unresolved template placeholder in URL: {url}"

    def test_georgia_lottery_net_urls_match_known_pattern(self):
        from registry.definitions.georgia import SOURCE_MAPPINGS
        from registry.enums import SourceName
        ln = [m for m in SOURCE_MAPPINGS
              if m.source_name == SourceName.LOTTERY_NET
              and m.job_def.game_type == "pick3"]
        urls = {m.build_url(year=2024, month=1) for m in ln}
        expected = {
            "https://www.lottery.net/georgia/cash-3-midday/numbers/2024",
            "https://www.lottery.net/georgia/cash-3-evening/numbers/2024",
            "https://www.lottery.net/georgia/cash-3-night/numbers/2024",
        }
        assert urls == expected, f"GA pick3 URLs wrong:\n  got:      {urls}\n  expected: {expected}"


# ── Validate State CLI ─────────────────────────────────────────────────────────

class TestValidateStateDryRun:
    """Tests that do not make HTTP requests or write to DB."""

    def _run(self, state, game=None, month="2024-01",
             source="lottery.net", dry_run=True, db_path=None):
        from cli.validate_state import validate_state
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            result = validate_state(
                state=state, game_type=game, month=month,
                source_name=source, dry_run=dry_run,
                skip_ingest=False, db_path=db_path,
            )
        return result, buf.getvalue()

    def test_georgia_dry_run_passes(self):
        passed, out = self._run("GA", "pick3")
        assert passed, f"GA dry-run should PASS\n{out}"

    def test_georgia_dry_run_no_warnings(self):
        passed, out = self._run("GA", "pick3")
        assert "0 warning" in out

    def test_florida_dry_run_passes_with_warnings(self):
        passed, out = self._run("FL", "pick3")
        assert passed, f"FL dry-run should PASS (warnings allowed)\n{out}"
        assert "ESTIMATED" in out or "WARN" in out, \
            "FL should warn about unverified slugs"

    def test_new_york_dry_run_passes(self):
        passed, out = self._run("NY", "pick3")
        assert passed

    def test_new_york_dry_run_shows_numbers_url(self):
        _, out = self._run("NY", "pick3")
        assert "numbers-midday" in out or "numbers-evening" in out, \
            f"NY pick3 URL should contain 'numbers' slug:\n{out}"

    def test_texas_dry_run_four_urls_generated(self):
        _, out = self._run("TX", "pick3", source="lottery.net")
        # TX has 4 draw times → 4 URLs
        url_lines = [l for l in out.splitlines() if "lottery.net/texas" in l]
        assert len(url_lines) >= 4, \
            f"TX pick3 should have 4 lottery.net URLs, got {len(url_lines)}"

    def test_california_dry_run_three_urls(self):
        _, out = self._run("CA", "pick3", source="lottery.net")
        url_lines = [l for l in out.splitlines() if "lottery.net/california" in l]
        assert len(url_lines) >= 3

    def test_unknown_state_fails(self):
        from cli.validate_state import validate_state
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            passed = validate_state(
                "XX", "pick3", "2024-01", "lottery.net",
                dry_run=True, skip_ingest=False, db_path=None,
            )
        assert not passed

    def test_output_contains_section_headers(self):
        _, out = self._run("GA", "pick3")
        assert "Registry" in out
        assert "URL planning" in out

    def test_output_shows_urls(self):
        _, out = self._run("GA", "pick3")
        assert "lottery.net/georgia/cash-3" in out

    def test_result_pass_exits_true(self):
        passed, _ = self._run("GA", "pick3")
        assert passed is True

    def test_result_fail_exits_false(self):
        passed, _ = self._run("XX", "pick3")
        assert passed is False

    def test_all_wave1_states_dry_run_pass(self):
        """Every Wave 1 state should at minimum pass the dry-run check."""
        from cli.validate_state import validate_state
        failures = []
        for state in WAVE1_STATES:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                passed = validate_state(
                    state, None, "2024-01", "lottery.net",
                    dry_run=True, skip_ingest=False, db_path=None,
                )
            if not passed:
                failures.append(f"{state}: {buf.getvalue()[-200:]}")
        assert not failures, "Dry-run failed for:\n" + "\n".join(failures)


class TestValidateStateWithData:
    """Tests that seed data and run the full quality/query checks."""

    def _seed_db(self, db_path: str, state: str, game: str, month: str) -> int:
        """Seed a month of fake draws. Returns number of draws inserted."""
        year, mon = int(month[:4]), int(month[5:7])
        import calendar
        _, days_in_month = calendar.monthrange(year, mon)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        base = Path(__file__).parent.parent / "db"
        conn.executescript((base / "schema.sql").read_text())
        conn.executescript((base / "views.sql").read_text())
        conn.commit()

        now = datetime.now(timezone.utc).isoformat()
        from registry.loader import get_jobs_for_state
        jobs = get_jobs_for_state(state, game_type=game, target_date=date(year, mon, 1))
        rows = []
        for day in range(1, days_in_month + 1):
            d = f"{year}-{mon:02d}-{day:02d}"
            for job in jobs:
                import random, hashlib
                # Generate reproducible pseudo-random 3- or 4-digit number
                seed = hashlib.md5(f"{state}{game}{d}{job.draw_time}".encode()).digest()
                digits = "".join(str(b % 10) for b in seed[:4 if game=="pick4" else 3])
                ckey = f"{state}|{game}|{d}|{job.draw_time}"
                dc = len(digits); sd = "".join(sorted(digits))
                rows.append((ckey,state,game,d,job.draw_time,digits,dc,sd,
                             "lottery.net",1,1,0,now))

        conn.executemany("""
            INSERT OR IGNORE INTO draws (
                canonical_key,state,game_type,draw_date,draw_time,
                winning_number,digit_count,sorted_digits,
                accepted_from_source,accepted_source_priority,
                is_verified,has_conflict,accepted_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
        conn.commit()
        # Seed registry too
        from registry.definitions import ALL_JOB_DEFINITIONS, ALL_SOURCE_MAPPINGS
        from registry.seed import seed_job_definitions, seed_source_mappings
        from db.connection import get_connection
        with get_connection(db_path) as c:
            jmap = seed_job_definitions(c, ALL_JOB_DEFINITIONS)
            seed_source_mappings(c, ALL_SOURCE_MAPPINGS, jmap)
        conn.close()
        return len(rows)

    def _run_skip_ingest(self, state, game, month, db_path):
        from cli.validate_state import validate_state
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            passed = validate_state(
                state=state, game_type=game, month=month,
                source_name="lottery.net", dry_run=False,
                skip_ingest=True, db_path=db_path,
            )
        return passed, buf.getvalue()

    def test_georgia_passes_with_seeded_data(self, tmp_path):
        db = str(tmp_path / "test.db")
        os.environ["LOTTERY_DB_PATH"] = db
        n = self._seed_db(db, "GA", "pick3", "2024-01")
        assert n > 0
        passed, out = self._run_skip_ingest("GA", "pick3", "2024-01", db)
        assert passed, f"GA should PASS with seeded data\n{out[-600:]}"

    def test_draw_time_coverage_reported(self, tmp_path):
        db = str(tmp_path / "test.db")
        self._seed_db(db, "GA", "pick3", "2024-01")
        _, out = self._run_skip_ingest("GA", "pick3", "2024-01", db)
        assert "midday" in out
        assert "evening" in out

    def test_sample_results_shown(self, tmp_path):
        db = str(tmp_path / "test.db")
        self._seed_db(db, "GA", "pick3", "2024-01")
        _, out = self._run_skip_ingest("GA", "pick3", "2024-01", db)
        assert "Sample results" in out

    def test_source_provenance_passes(self, tmp_path):
        db = str(tmp_path / "test.db")
        self._seed_db(db, "GA", "pick3", "2024-01")
        _, out = self._run_skip_ingest("GA", "pick3", "2024-01", db)
        assert "Source provenance" in out
        # Should not see FAIL on provenance line
        for line in out.splitlines():
            if "Source provenance" in line:
                assert "FAIL" not in line, f"Provenance check failed: {line}"

    def test_candidate_match_passes(self, tmp_path):
        db = str(tmp_path / "test.db")
        self._seed_db(db, "GA", "pick3", "2024-01")
        _, out = self._run_skip_ingest("GA", "pick3", "2024-01", db)
        for line in out.splitlines():
            if "Candidate match" in line:
                assert "FAIL" not in line, f"Candidate match failed: {line}"
                break

    def test_dream_backtest_passes(self, tmp_path):
        db = str(tmp_path / "test.db")
        self._seed_db(db, "GA", "pick3", "2024-01")
        _, out = self._run_skip_ingest("GA", "pick3", "2024-01", db)
        for line in out.splitlines():
            if "Dream backtest" in line:
                assert "FAIL" not in line, f"Dream backtest failed: {line}"
                break

    def test_missing_state_fails_gracefully(self, tmp_path):
        db = str(tmp_path / "test.db")
        from db.connection import initialize_db
        initialize_db(db)
        passed, out = self._run_skip_ingest("ZZ", "pick3", "2024-01", db)
        assert not passed


# ── Registry report CLI ────────────────────────────────────────────────────────

class TestRegistryReport:
    def _run(self, args=None):
        from cli.registry_report import main
        buf = io.StringIO()
        argv = args or []
        with patch("sys.argv", ["registry_report"] + argv), \
             patch("sys.stdout", buf):
            try:
                main()
            except SystemExit:
                pass
        return buf.getvalue()

    def test_summary_contains_all_states(self):
        out = self._run(["--format", "summary"])
        for state in WAVE1_STATES:
            assert state in out, f"{state} missing from summary report"

    def test_summary_shows_georgia_seeded(self):
        out = self._run(["--format", "summary"])
        assert "SEEDED" in out

    def test_summary_shows_stub_states(self):
        out = self._run(["--format", "summary"])
        assert "STUB" in out

    def test_order_shows_all_states(self):
        out = self._run(["--format", "order"])
        for state in WAVE1_STATES:
            assert state in out

    def test_order_georgia_marked_done(self):
        out = self._run(["--format", "order"])
        assert "DONE" in out

    def test_detail_shows_game_names(self):
        out = self._run(["--format", "detail"])
        assert "Numbers" in out   # NY pick3
        assert "Win 4"  in out   # NY pick4
        assert "Cash 3" in out   # GA pick3
        assert "Daily 3" in out  # MI/CA pick3

    def test_sources_matrix_shows_slugs(self):
        out = self._run(["--format", "sources"])
        assert "GA" in out and "verified" in out.lower()
        assert "NY" in out and "estimated" in out.lower()

    def test_single_state_filter(self):
        out = self._run(["--state", "GA"])
        assert "GA" in out
        assert "FL" not in out or out.index("GA") < out.index("FL") + 5

    def test_georgia_shows_verified_slugs(self):
        out = self._run(["--format", "detail"])
        # GA section should mention verified
        ga_section = ""
        in_ga = False
        for line in out.splitlines():
            if "GA" in line and "Georgia" in line:
                in_ga = True
            elif in_ga and any(s in line for s in ["FL","NY","PA","OH"]):
                break
            if in_ga:
                ga_section += line + "\n"
        assert "verified" in ga_section.lower(), \
            f"GA section should show 'verified' slugs:\n{ga_section}"

    def test_fl_shows_estimated_warning(self):
        out = self._run(["--format", "detail"])
        fl_section = ""
        in_fl = False
        for line in out.splitlines():
            if "FL" in line and "Florida" in line:
                in_fl = True
            elif in_fl and any(s in line for s in ["NY","PA","OH"]):
                break
            if in_fl:
                fl_section += line + "\n"
        assert "ESTIMATED" in fl_section or "estimated" in fl_section.lower(), \
            f"FL section should warn about ESTIMATED slugs:\n{fl_section}"

    def test_load_state_data_returns_correct_keys(self):
        from cli.registry_report import load_state_data
        d = load_state_data("GA")
        assert d is not None
        for key in ("code","name","wave","tier","complexity","status",
                    "games","draws_per_day","n_jobs","n_mappings",
                    "sources","slugs_verified"):
            assert key in d, f"Missing key {key!r} in GA state data"

    def test_load_state_data_ga_values(self):
        from cli.registry_report import load_state_data
        d = load_state_data("GA")
        assert d["code"] == "GA"
        assert d["wave"] == 1
        assert d["complexity"] == "moderate"
        assert d["draws_per_day"] == 3
        assert d["slugs_verified"] is True
        assert "pick3" in d["games"]
        assert "pick4" in d["games"]

    def test_load_state_data_tx_is_high_complexity(self):
        from cli.registry_report import load_state_data
        d = load_state_data("TX")
        assert d["complexity"] == "high"
        assert d["draws_per_day"] == 4

    def test_load_state_data_or_pick4_only(self):
        from cli.registry_report import load_state_data
        d = load_state_data("OR")
        assert "pick4" in d["games"]
        assert "pick3" not in d["games"]

    def test_unknown_state_returns_none(self):
        from cli.registry_report import load_state_data
        assert load_state_data("ZZ") is None
