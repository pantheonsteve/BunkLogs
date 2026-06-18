#!/usr/bin/env python3
"""Parallel POST smoke test for end-of-day submission idempotency.

Usage (staging or local with a counselor JWT):

  export BASE_URL=https://admin.bunklogs.net
  export ACCESS_TOKEN=<jwt>
  export SUBJECT_ID=123
  export BUNK_ID=456
  python scripts/eod_submission_load_smoke.py

Fires 50 unique POSTs plus 10 duplicate replays of the first UUID.
Expects 0 HTTP 500 responses and duplicate replays to return 200.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
import uuid
from urllib import error, request


def _post(url: str, token: str, payload: dict) -> tuple[int, str]:
    data = json.dumps(payload).encode()
    req = request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read(200).decode(errors="replace")
    except error.HTTPError as exc:
        body = exc.read(200).decode(errors="replace")
        return exc.code, body


def main() -> int:
    base = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
    token = os.environ.get("ACCESS_TOKEN")
    subject_id = os.environ.get("SUBJECT_ID")
    bunk_id = os.environ.get("BUNK_ID")

    if not token or not subject_id or not bunk_id:
        print(
            "Set ACCESS_TOKEN, SUBJECT_ID, and BUNK_ID env vars.",
            file=sys.stderr,
        )
        return 1

    url = f"{base}/api/v1/counselor/camper-reflections/"
    subject_id = int(subject_id)
    bunk_id = int(bunk_id)

    def make_payload(csid: str | None = None) -> dict:
        return {
            "subject_id": subject_id,
            "assignment_group_id": bunk_id,
            "answers": {"note": "load smoke"},
            "language": "en",
            "team_visibility": "team",
            "client_submission_id": csid or str(uuid.uuid4()),
        }

    first_csid = str(uuid.uuid4())
    jobs: list[tuple[str, dict]] = [(first_csid, make_payload(first_csid))]
    jobs.extend((str(uuid.uuid4()), make_payload()) for _ in range(49))
    jobs.extend((first_csid, make_payload(first_csid)) for _ in range(10))

    started = time.perf_counter()
    results: list[tuple[int, str]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(_post, url, token, payload) for _, payload in jobs]
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    elapsed = time.perf_counter() - started
    statuses = [code for code, _ in results]
    failures = [code for code in statuses if code >= 500]
    dup_codes = statuses[50:60]

    print(f"Completed {len(results)} requests in {elapsed:.2f}s")
    print(f"Status histogram: { {c: statuses.count(c) for c in sorted(set(statuses))} }")
    print(f"Duplicate replay statuses (expect all 200): {dup_codes}")

    if failures:
        print(f"FAIL: {len(failures)} server errors", file=sys.stderr)
        return 1
    if not all(code in (200, 201) for code in dup_codes):
        print("FAIL: duplicate replays did not all return 200/201", file=sys.stderr)
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
