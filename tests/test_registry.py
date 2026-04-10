"""
lottery_engine/tests/test_registry.py
"""
import pytest
from datetime import date
from registry.loader import (
    get_active_jobs, get_jobs_for_state,
    get_source_mappings_for_job, get_all_states,
    get_game_types_for_state,
)
from registry.enums import DrawTime, SourceName, SOURCE_PRIORITIES
from registry.definitions.georgia import JOB_DEFINITIONS as GA_JOBS


class TestJobDefinitions:
    def test_georgia_jobs_loaded(self):
        jobs = get_jobs_for_state("GA")
        assert len(jobs) > 0

    def test_georgia_has_pick3_and_pick4(self):
        games = get_game_types_for_state("GA")
        assert "pick3" in games
        assert "pick4" in games

    def test_georgia_has_midday_evening(self):
        jobs = get_jobs_for_state("GA")
        times = {j.draw_time for j in jobs}
        assert "midday" in times
        assert "evening" in times

    def test_florida_loaded(self):
        jobs = get_jobs_for_state("FL")
        assert len(jobs) > 0

    def test_all_states_returns_list(self):
        states = get_all_states()
        assert "GA" in states
        assert "FL" in states

    def test_canonical_time_key_defaults_to_draw_time(self):
        for job in GA_JOBS:
            assert job.canonical_time_key == job.draw_time

    def test_draw_time_values_are_canonical(self):
        valid = DrawTime.values()
        for job in get_active_jobs():
            assert job.draw_time in valid, f"Non-canonical draw_time: {job.draw_time!r} in {job.draw_label}"

    def test_all_game_types_are_canonical(self):
        from registry.enums import GameType
        valid = GameType.values()
        for job in get_active_jobs():
            assert job.game_type in valid, f"Non-canonical game_type: {job.game_type!r}"

    def test_night_draw_has_active_start_date(self):
        """Night draws added after launch must have an active_start_date."""
        night_jobs = [j for j in GA_JOBS if j.draw_time == "night"]
        assert len(night_jobs) > 0
        for job in night_jobs:
            assert job.active_start_date is not None, \
                f"Night draw {job.draw_label} missing active_start_date"


class TestLifecycleFiltering:
    def test_night_draw_not_active_before_start(self):
        night_jobs = [j for j in GA_JOBS if j.draw_time == "night"]
        for job in night_jobs:
            if job.active_start_date:
                early_date = date(job.active_start_date.year - 1, 1, 1)
                assert not job.active_on(early_date), \
                    f"{job.draw_label} should not be active on {early_date}"

    def test_standard_draw_active_on_recent_date(self):
        midday_jobs = [j for j in GA_JOBS if j.draw_time == "midday"]
        recent = date(2024, 6, 1)
        for job in midday_jobs:
            assert job.active_on(recent), f"{job.draw_label} should be active on {recent}"

    def test_get_active_jobs_filters_by_date(self):
        # Before night draws existed
        early = date(2005, 1, 1)
        jobs = get_jobs_for_state("GA", target_date=early)
        night_times = [j for j in jobs if j.draw_time == "night"]
        assert len(night_times) == 0, "Night draws should not appear before active_start_date"

    def test_covers_year_respects_source_min(self):
        for job in GA_JOBS:
            if job.source_min_year:
                assert not job.covers_year(job.source_min_year - 1)
                assert job.covers_year(job.source_min_year)


class TestSourceMappings:
    def test_georgia_has_lottery_net_mappings(self):
        jobs = get_jobs_for_state("GA")
        for job in jobs:
            mappings = get_source_mappings_for_job(job, source_name=SourceName.LOTTERY_NET)
            assert len(mappings) >= 1, f"No lottery.net mapping for {job.draw_label}"

    def test_mappings_sorted_by_priority(self):
        jobs = get_jobs_for_state("GA")
        for job in jobs:
            mappings = get_source_mappings_for_job(job)
            priorities = [m.source_priority for m in mappings]
            assert priorities == sorted(priorities), \
                f"Mappings not sorted by priority for {job.draw_label}"

    def test_lottery_net_is_highest_priority(self):
        jobs = get_jobs_for_state("GA")
        for job in jobs:
            mappings = get_source_mappings_for_job(job)
            if mappings:
                assert mappings[0].source_priority == SOURCE_PRIORITIES[SourceName.LOTTERY_NET]

    def test_url_templates_contain_year(self):
        jobs = get_jobs_for_state("GA")
        for job in jobs:
            mappings = get_source_mappings_for_job(job, source_name=SourceName.LOTTERY_NET)
            for m in mappings:
                assert m.url_template is not None
                assert "{year}" in m.url_template
            assert "{year}" in m.url_template

    def test_build_url(self):
        jobs = get_jobs_for_state("GA")
        for job in jobs:
            mappings = get_source_mappings_for_job(job, source_name=SourceName.LOTTERY_NET)
            for m in mappings:
                url = m.build_url(year=2024, month=3)
                assert url is not None
                assert "2024" in url
                assert "2024" in url


class TestSeedRoundtrip:
    def test_seed_and_verify(self, seeded_db):
        rows = seeded_db.execute(
            "SELECT COUNT(*) FROM draw_job_definitions"
        ).fetchone()[0]
        assert rows > 0

    def test_seed_source_mappings(self, seeded_db):
        rows = seeded_db.execute(
            "SELECT COUNT(*) FROM source_job_mappings"
        ).fetchone()[0]
        assert rows > 0

    def test_seed_idempotent(self, seeded_db):
        """Running seed twice should not duplicate rows."""
        from registry.definitions import ALL_JOB_DEFINITIONS, ALL_SOURCE_MAPPINGS
        from registry.seed import seed_job_definitions, seed_source_mappings
        count_before = seeded_db.execute(
            "SELECT COUNT(*) FROM draw_job_definitions"
        ).fetchone()[0]
        job_id_map = seed_job_definitions(seeded_db, ALL_JOB_DEFINITIONS)
        seed_source_mappings(seeded_db, ALL_SOURCE_MAPPINGS, job_id_map)
        seeded_db.commit()
        count_after = seeded_db.execute(
            "SELECT COUNT(*) FROM draw_job_definitions"
        ).fetchone()[0]
        assert count_before == count_after
