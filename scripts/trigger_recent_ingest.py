#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.request


def main() -> int:
    base = os.environ["LOTTERY_ENGINE_URL"].strip().rstrip("/")
    token = os.environ["INGEST_ADMIN_TOKEN"].strip()
    days_back = int(os.environ.get("INGEST_DAYS_BACK", "3").strip())

    payload = {"days_back": days_back}
    req = urllib.request.Request(
        f"{base}/admin/ingest/recent",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Ingest-Token": token,
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=1800) as resp:
        body = resp.read().decode("utf-8")
        print(body)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    