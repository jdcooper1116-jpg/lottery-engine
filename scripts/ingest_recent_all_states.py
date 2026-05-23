#!/usr/bin/env python3
"""
scripts/ingest_recent_all_states.py

Run recent ingest for all supported state/game combos.

Improvements over original:
  - Default source is blank (all sources) — no hard-lock to lottery.net.
    Pass --source lottery.net explicitly if you want to pin a source.
  - Parses each subprocess output for raw_results / observations_written.
  - Tracks totals: raw_results_total, observations_written_total,
    states_with_zero_rows, fetch_timeout_count, fetch_error_count.
  - Returns exit code 1 when raw_results_total == 0 OR
    observations_written_total == 0 (silent all-zero success is no longer allowed).
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest recent results for all supported state/game combos.")
    p.add_argument("--days-back", type=int, default=int(os.environ.get("INGEST_DAYS_BACK", "3")))
    p.add_argument("--db-path",   default=os.environ.get("LOTTERY_DB_PATH", "/data/history_all_states.db"))
    # Default is blank (all sources). Explicitly pass --source to pin one.
    p.add_argument("--source",    default=os.environ.get("INGEST_SOURCE", ""),
                   help="Source name to pin (blank = all sources, recommended)")
    p.add_argument("--status-path", default=os.environ.get("INGEST_STATUS_PATH", "/data/ingest_recent_status.json"))
    p.add_argument("--lock-path",   default=os.environ.get("INGEST_LOCK_PATH", "/tmp/ingest_recent_all_states.lock"))
    return p.parse_args()


def get_supported_pairs(db_path: str) -> list[tuple[str, str]]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT DISTINCT state, game_type
            FROM draws
            WHERE game_type IN ('pick3', 'pick4')
            ORDER BY state, game_type
            """
        ).fetchall()
        return [(r[0], r[1]) for r in rows]
    finally:
        conn.close()


def _parse_ingest_output(stdout: str, stderr: str) -> dict:
    """
    Extract raw_results and observations_written from cli.ingest stdout/stderr.
    The ingest runner logs: "Ingest complete: {'tasks_run': N, 'raw_results': M, ...}"
    """
    raw_results       = 0
    observations      = 0
    timeout_count     = 0
    error_count       = 0

    # Look for the summary dict logged by orchestrator/runner.py
    for line in (stdout + "\n" + stderr).splitlines():
        if "Ingest complete:" in line:
            try:
                m = re.search(r"\{.*\}", line)
                if m:
                    d = json.loads(m.group(0).replace("'", "\""))
                    raw_results  = int(d.get("raw_results", 0))
                    observations = int(d.get("observations_written", 0))
            except Exception:
                pass
        # Count timeout/error lines from the logger
        if "timeout" in line.lower() or "Timeout" in line:
            timeout_count += 1
        if "Fetch failed" in line or "HTTP error" in line or "error_count" in line.lower():
            error_count += 1

    return {
        "raw_results":       raw_results,
        "observations":      observations,
        "timeout_count":     timeout_count,
        "error_count":       error_count,
    }


def main() -> int:
    args = parse_args()

    today      = dt.date.today()
    start_date = (today - dt.timedelta(days=args.days_back)).isoformat()
    end_date   = today.isoformat()

    status_path = Path(args.status_path)
    status_path.parent.mkdir(parents=True, exist_ok=True)

    lock_file = open(args.lock_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Recent-ingest job is already running. Exiting cleanly.")
        return 0

    started_at = dt.datetime.utcnow().isoformat() + "Z"
    results: list[dict] = []

    try:
        pairs = get_supported_pairs(args.db_path)
        print(f"Found {len(pairs)} supported state/game pairs")
        print(f"Ingest window: {start_date} to {end_date}")
        print(f"Source: {args.source or '(all sources)'}")
        print(f"DB: {args.db_path}")

        raw_results_total          = 0
        observations_written_total = 0
        states_with_zero_rows:  list[str] = []
        fetch_timeout_count        = 0
        fetch_error_count          = 0

        for state, game_type in pairs:
            cmd = [
                sys.executable, "-m", "cli.ingest",
                "--state", state,
                "--game",  game_type,
                "--start", start_date,
                "--end",   end_date,
            ]
            # Only append --source when explicitly provided — no hard-lock default
            if args.source:
                cmd += ["--source", args.source]

            print("\nRUN:", " ".join(cmd))
            proc = subprocess.run(cmd, capture_output=True, text=True)

            parsed = _parse_ingest_output(proc.stdout, proc.stderr)
            raw    = parsed["raw_results"]
            obs    = parsed["observations"]

            raw_results_total          += raw
            observations_written_total += obs
            fetch_timeout_count        += parsed["timeout_count"]
            fetch_error_count          += parsed["error_count"]

            if raw == 0:
                states_with_zero_rows.append(f"{state}/{game_type}")

            results.append({
                "state":             state,
                "game_type":         game_type,
                "return_code":       proc.returncode,
                "raw_results":       raw,
                "observations":      obs,
                "timeout_count":     parsed["timeout_count"],
                "error_count":       parsed["error_count"],
                "stdout_tail":       proc.stdout[-1500:],
                "stderr_tail":       proc.stderr[-1500:],
            })

        finished_at = dt.datetime.utcnow().isoformat() + "Z"
        failures    = [r for r in results if r["return_code"] != 0]

        print(f"\n{'='*60}")
        print(f"INGEST SUMMARY")
        print(f"  raw_results_total:          {raw_results_total}")
        print(f"  observations_written_total: {observations_written_total}")
        print(f"  states_with_zero_rows:      {len(states_with_zero_rows)}")
        print(f"  fetch_timeout_count:        {fetch_timeout_count}")
        print(f"  fetch_error_count:          {fetch_error_count}")
        print(f"  subprocess_failures:        {len(failures)}")
        if states_with_zero_rows:
            print(f"  ZERO-ROW STATES: {states_with_zero_rows}")
        print(f"{'='*60}")

        status = {
            "started_at":                started_at,
            "finished_at":               finished_at,
            "db_path":                   args.db_path,
            "source":                    args.source or "(all sources)",
            "window_start":              start_date,
            "window_end":                end_date,
            "pair_count":                len(results),
            "failure_count":             len(failures),
            "raw_results_total":         raw_results_total,
            "observations_written_total":observations_written_total,
            "states_with_zero_rows":     states_with_zero_rows,
            "fetch_timeout_count":       fetch_timeout_count,
            "fetch_error_count":         fetch_error_count,
            "results":                   results,
        }

        status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

        print(f"Status written to {status_path}")
        print(f"Failures: {len(failures)}")

        # Exit 1 if all-zero — do not silently succeed on empty ingest
        if raw_results_total == 0:
            print("ERROR: raw_results_total == 0 — no data was fetched.", file=sys.stderr)
            return 1
        if observations_written_total == 0:
            print("WARNING: observations_written_total == 0 — rows were fetched but none written.",
                  file=sys.stderr)
            return 1

        return 1 if failures else 0

    finally:
        lock_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
