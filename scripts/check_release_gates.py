"""Fail closed unless every required release workflow passed on the exact SHA.

Input is the GitHub Actions /actions/runs API JSON response on stdin.
No network calls and no external dependencies: easy to regression-test.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

REQUIRED_WORKFLOWS = frozenset(
    {"Backend Tests", "Frontend Tests", "Full Stack E2E", "Release Metadata"}
)
COMMIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


def failures_for_release(payload: dict[str, Any], sha: str) -> list[str]:
    if not COMMIT_SHA.fullmatch(sha):
        return ["expected commit must be a full lowercase 40-character SHA"]
    if not isinstance(payload.get("workflow_runs"), list):
        return ["missing GitHub workflow_runs result"]

    latest: dict[str, dict[str, Any]] = {}
    for run in payload["workflow_runs"]:
        if (
            not isinstance(run, dict)
            or run.get("head_sha") != sha
            or run.get("head_branch") != "main"
            or run.get("event") not in {"push", "workflow_dispatch"}
            or run.get("name") not in REQUIRED_WORKFLOWS
        ):
            continue
        name = run["name"]
        previous = latest.get(name)
        def order_key(item: dict[str, Any]) -> tuple[str, int, int]:
            return (
                str(item.get("created_at") or ""),
                int(item.get("run_attempt") or 0),
                int(item.get("id") or 0),
            )
        if previous is None or order_key(run) > order_key(previous):
            latest[name] = run

    failures: list[str] = []
    for name in sorted(REQUIRED_WORKFLOWS):
        run = latest.get(name)
        if run is None:
            failures.append(f"{name}: no matching run on main at {sha}")
        elif run.get("status") != "completed":
            failures.append(f"{name}: not completed")
        elif run.get("conclusion") != "success":
            failures.append(
                f"{name}: conclusion={run.get('conclusion')!r}"
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()
    payload = json.load(sys.stdin)
    failures = failures_for_release(payload, args.sha)
    if failures:
        for failure in failures:
            print(f"BLOCKED: {failure}", file=sys.stderr)
        return 1
    print(f"Release CI gates passed for exact main commit {args.sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
