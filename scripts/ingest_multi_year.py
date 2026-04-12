#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run smart ingester across multiple years.")
    parser.add_argument(
        "--years",
        nargs="+",
        required=True,
        help="Years to ingest, e.g. 2021 2020 2019",
    )
    parser.add_argument(
        "--states-file",
        default="scripts/state_list_2024_broad.txt",
        help="State list file to use",
    )
    args = parser.parse_args()

    states_file = Path(args.states_file)
    if not states_file.exists():
        raise SystemExit(f"States file not found: {states_file}")

    for year in args.years:
        print()
        print("=" * 72)
        print(f"RUNNING INGEST FOR YEAR {year}")
        print("=" * 72)
        cmd = [
            sys.executable,
            "scripts/ingest_year_smart.py",
            "--year",
            str(year),
            "--states-file",
            str(states_file),
        ]
        cp = subprocess.run(cmd, text=True)
        if cp.returncode != 0:
            print(f"Year {year} exited with code {cp.returncode}")
        else:
            print(f"Year {year} complete.")

    print("\nAll requested years processed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
