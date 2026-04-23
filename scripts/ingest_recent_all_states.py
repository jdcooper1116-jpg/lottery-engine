#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest recent results for all supported state/game combos.")
    p.add_argument("--days-back", type=int, default=int(os.environ.get("INGEST_DAYS_BACK", "3")))
    p.add_argument("--db-path", default=os.environ.get("LOTTERY_DB_PATH", "/data/history_all_states.db"))
    p.add_argument("--source", default=os.environ.get("INGEST_SOURCE", "lottery.net"))
    p.add_argument("--status-path", default=os.environ.get("INGEST_STATUS_PATH", "/data/ingest_recent_status.json"))
    p.add_argument("--lock-path", default=os.environ.get("INGEST_LOCK_PATH", "/tmp/ingest_recent_all_states.lock"))
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


def main() -> int:
    args = parse_args()

    today = dt.date.today()
    start_date = (today - dt.timedelta(days=args.days_back)).isoformat()
    end_date = today.isoformat()

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
        print(f"Source: {args.source}")
        print(f"DB: {args.db_path}")

        for state, game_type in pairs:
            cmd = [
                sys.executable,
                "-m",
                "cli.ingest",
                "--state",
                state,
                "--game",
                game_type,
                "--start",
                start_date,
                "--end",
                end_date,
                "--source",
                args.source,
            ]
            print("\nRUN:", " ".join(cmd))
            proc = subprocess.run(cmd, capture_output=True, text=True)

            results.append(
                {
                    "state": state,
                    "game_type": game_type,
                    "return_code": proc.returncode,
                    "stdout_tail": proc.stdout[-1500:],
                    "stderr_tail": proc.stderr[-1500:],
                }
            )

        finished_at = dt.datetime.utcnow().isoformat() + "Z"
        failures = [r for r in results if r["return_code"] != 0]

        status = {
            "started_at": started_at,
            "finished_at": finished_at,
            "db_path": args.db_path,
            "source": args.source,
            "window_start": start_date,
            "window_end": end_date,
            "pair_count": len(results),
            "failure_count": len(failures),
            "results": results,
        }

        status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

        print("\nDone.")
        print(f"Status written to {status_path}")
        print(f"Failures: {len(failures)}")

        return 1 if failures else 0

    finally:
        lock_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
    