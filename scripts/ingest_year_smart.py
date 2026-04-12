#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


DEFAULT_GAMES = ["pick3", "pick4"]

UNSUPPORTED_STATE_GAMES: set[tuple[str, str]] = {
    ("OR", "pick3"),
}


@dataclass
class RunResult:
    state: str
    game: str
    year: int
    status: str
    reason: str
    returncode: int
    command: str
    stdout_tail: str
    stderr_tail: str


def run_cmd(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )


def tail(text: str, lines: int = 20) -> str:
    if not text:
        return ""
    parts = text.strip().splitlines()
    return "\n".join(parts[-lines:])


def classify_validate_output(cp: subprocess.CompletedProcess[str]) -> tuple[str, str]:
    out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    lower = out.lower()

    if cp.returncode != 0:
        if "no job definitions found" in lower:
            return "skipped", "unsupported_no_job_definitions"
        if "invalid choice" in lower:
            return "skipped", "unsupported_invalid_choice"
        if "not found" in lower and "registry" in lower:
            return "skipped", "unsupported_registry_missing"
        return "failed", "validate_command_failed"

    if "result: fail" in lower:
        if "no job definitions found" in lower:
            return "skipped", "unsupported_no_job_definitions"
        return "failed", "validate_failed"

    if "result: pass" in lower:
        if "warning" in lower:
            return "validated_with_warnings", "validate_pass_with_warnings"
        return "validated", "validate_pass"

    return "failed", "validate_unknown_result"


def classify_ingest_output(cp: subprocess.CompletedProcess[str]) -> tuple[str, str]:
    out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    lower = out.lower()

    if cp.returncode != 0:
        if "no job definitions found" in lower:
            return "skipped", "unsupported_no_job_definitions"
        return "failed", "ingest_command_failed"

    if "accepted:" in lower or "duplicate:" in lower or "reconcile summary" in lower:
        if "accepted: 0" in lower and "duplicate:" in lower:
            return "ingested", "duplicates_only_existing_data"
        return "ingested", "ingest_success"

    if "wrote" in lower or "observations" in lower:
        return "ingested", "ingest_success"

    return "ingested", "ingest_completed_no_reconcile_summary"


def load_states(path: Path) -> list[str]:
    states: list[str] = []
    for line in path.read_text().splitlines():
        s = line.strip().upper()
        if not s or s.startswith("#"):
            continue
        states.append(s)
    return states


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smart yearly ingest runner with CSV summary.")
    parser.add_argument("--year", type=int, required=True, help="Year to ingest, e.g. 2024")
    parser.add_argument(
        "--states-file",
        type=Path,
        default=Path("scripts/state_list.txt"),
        help="Text file with one state code per line",
    )
    parser.add_argument(
        "--games",
        nargs="*",
        default=DEFAULT_GAMES,
        help="Games to attempt, default: pick3 pick4",
    )
    parser.add_argument(
        "--source",
        default="lottery.net",
        help="Source name for validate/ingest, default: lottery.net",
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        default=None,
        help="Output CSV path. Default: logs/ingest_summary_<year>.csv",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="Directory for per-run logs",
    )
    parser.add_argument(
        "--skip-ingest-on-validate-warning",
        action="store_true",
        help="If set, do not ingest states that only validate with warnings",
    )
    args = parser.parse_args()

    states = load_states(args.states_file)
    summary_csv = args.summary_csv or Path(f"logs/ingest_summary_{args.year}.csv")
    ensure_parent(summary_csv)
    args.log_dir.mkdir(parents=True, exist_ok=True)

    results: list[RunResult] = []

    start_date = f"{args.year}-01-01"
    end_date = f"{args.year}-12-31"

    print(f"Loaded {len(states)} states from {args.states_file}")
    print(f"Games: {', '.join(args.games)}")
    print(f"Year: {args.year}")
    print()

    for state in states:
        for game in args.games:
            print(f"=== {state} {game} {args.year} ===")

            if (state, game) in UNSUPPORTED_STATE_GAMES:
                print("SKIP preset: unsupported_state_game_combo")
                results.append(
                    RunResult(
                        state=state,
                        game=game,
                        year=args.year,
                        status="skipped",
                        reason="unsupported_state_game_combo",
                        returncode=0,
                        command="preset-skip",
                        stdout_tail="",
                        stderr_tail="",
                    )
                )
                print()
                continue

            validate_cmd = [
                sys.executable,
                "-m",
                "cli.validate_state",
                "--state",
                state,
                "--game",
                game,
                "--month",
                f"{args.year}-01",
                "--source",
                args.source,
                "--dry-run",
            ]
            vcp = run_cmd(validate_cmd)
            vstatus, vreason = classify_validate_output(vcp)

            validate_log = args.log_dir / f"validate_{state}_{game}_{args.year}.log"
            validate_log.write_text(
                f"$ {' '.join(validate_cmd)}\n\nSTDOUT:\n{vcp.stdout}\n\nSTDERR:\n{vcp.stderr}"
            )

            if vstatus == "skipped":
                print(f"SKIP validate: {vreason}")
                results.append(
                    RunResult(
                        state=state,
                        game=game,
                        year=args.year,
                        status="skipped",
                        reason=vreason,
                        returncode=vcp.returncode,
                        command=" ".join(validate_cmd),
                        stdout_tail=tail(vcp.stdout),
                        stderr_tail=tail(vcp.stderr),
                    )
                )
                print()
                continue

            if vstatus == "failed":
                print(f"FAIL validate: {vreason}")
                results.append(
                    RunResult(
                        state=state,
                        game=game,
                        year=args.year,
                        status="failed",
                        reason=vreason,
                        returncode=vcp.returncode,
                        command=" ".join(validate_cmd),
                        stdout_tail=tail(vcp.stdout),
                        stderr_tail=tail(vcp.stderr),
                    )
                )
                print()
                continue

            print(f"VALIDATE: {vstatus} ({vreason})")

            if vstatus == "validated_with_warnings" and args.skip_ingest_on_validate_warning:
                results.append(
                    RunResult(
                        state=state,
                        game=game,
                        year=args.year,
                        status="skipped",
                        reason="skipped_due_to_validate_warning",
                        returncode=vcp.returncode,
                        command=" ".join(validate_cmd),
                        stdout_tail=tail(vcp.stdout),
                        stderr_tail=tail(vcp.stderr),
                    )
                )
                print("SKIP ingest due to warning policy")
                print()
                continue

            ingest_cmd = [
                sys.executable,
                "-m",
                "cli.ingest",
                "--state",
                state,
                "--game",
                game,
                "--start",
                start_date,
                "--end",
                end_date,
                "--source",
                args.source,
            ]
            icp = run_cmd(ingest_cmd)
            istatus, ireason = classify_ingest_output(icp)

            ingest_log = args.log_dir / f"ingest_{state}_{game}_{args.year}.log"
            ingest_log.write_text(
                f"$ {' '.join(ingest_cmd)}\n\nSTDOUT:\n{icp.stdout}\n\nSTDERR:\n{icp.stderr}"
            )

            print(f"INGEST: {istatus} ({ireason})")
            results.append(
                RunResult(
                    state=state,
                    game=game,
                    year=args.year,
                    status=istatus,
                    reason=ireason,
                    returncode=icp.returncode,
                    command=" ".join(ingest_cmd),
                    stdout_tail=tail(icp.stdout),
                    stderr_tail=tail(icp.stderr),
                )
            )
            print()

    with summary_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "state",
                "game",
                "year",
                "status",
                "reason",
                "returncode",
                "command",
                "stdout_tail",
                "stderr_tail",
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "state": r.state,
                    "game": r.game,
                    "year": r.year,
                    "status": r.status,
                    "reason": r.reason,
                    "returncode": r.returncode,
                    "command": r.command,
                    "stdout_tail": r.stdout_tail,
                    "stderr_tail": r.stderr_tail,
                }
            )

    print(f"Summary written to: {summary_csv}")

    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    print("Status counts:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
