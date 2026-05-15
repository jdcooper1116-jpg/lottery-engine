#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


def post_json(url: str, token: str, payload: dict, timeout: int = 1800) -> str:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Ingest-Token": token,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def get_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def main() -> int:
    base = os.environ["LOTTERY_ENGINE_URL"].strip().rstrip("/")
    token = os.environ["INGEST_ADMIN_TOKEN"].strip()
    days_back = int(os.environ.get("INGEST_DAYS_BACK", "3").strip())

    max_attempts = int(os.environ.get("INGEST_TRIGGER_MAX_ATTEMPTS", "5").strip())
    base_sleep = float(os.environ.get("INGEST_TRIGGER_BASE_SLEEP", "10").strip())

    payload = {"days_back": days_back}

    health_url = f"{base}/health"
    ingest_url = f"{base}/admin/ingest/recent"

    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Optional readiness check
            try:
                health = get_text(health_url, timeout=30)
                print(f"[attempt {attempt}] health ok: {health}")
            except Exception as e:
                print(f"[attempt {attempt}] health check failed: {e}")

            body = post_json(ingest_url, token, payload, timeout=1800)
            print(body)
            return 0

        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            ConnectionResetError,
            ConnectionError,
            OSError,
        ) as e:
            last_error = e
            print(f"[attempt {attempt}/{max_attempts}] ingest trigger failed: {repr(e)}", file=sys.stderr)

            if attempt == max_attempts:
                break

            sleep_for = base_sleep * (2 ** (attempt - 1))
            print(f"[attempt {attempt}] sleeping {sleep_for:.1f}s before retry...", file=sys.stderr)
            time.sleep(sleep_for)

    print(f"Final failure after {max_attempts} attempts: {repr(last_error)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
