"""Security regressions for manual release gating (stdlib only)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_release_gates import REQUIRED_WORKFLOWS, failures_for_release  # noqa: E402

SHA = "a" * 40
OTHER_SHA = "b" * 40


def run(
    name: str,
    *,
    sha: str = SHA,
    conclusion: str = "success",
    status: str = "completed",
    event: str = "push",
    branch: str = "main",
    timestamp: str = "2026-10-12T15:30:00Z",
) -> dict:
    return dict(
        name=name,
        head_sha=sha,
        conclusion=conclusion,
        status=status,
        event=event,
        head_branch=branch,
        created_at=timestamp,
        id=100,
        run_attempt=1,
    )


class ReleaseGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.all_green = {
            "workflow_runs": [run(name) for name in REQUIRED_WORKFLOWS]
        }

    def test_exact_commit_all_green_accepted(self) -> None:
        self.assertEqual(failures_for_release(self.all_green, SHA), [])

    def test_missing_workflow_fails_closed(self) -> None:
        runs = self.all_green["workflow_runs"][:-1]
        self.assertEqual(len(failures_for_release({"workflow_runs": runs}, SHA)), 1)

    def test_green_on_old_commit_does_not_count(self) -> None:
        runs = [run(name, sha=OTHER_SHA) for name in REQUIRED_WORKFLOWS]
        self.assertEqual(len(failures_for_release({"workflow_runs": runs}, SHA)), 4)

    def test_pr_event_does_not_count_as_production_gate(self) -> None:
        runs = [run(name, event="pull_request") for name in REQUIRED_WORKFLOWS]
        self.assertEqual(len(failures_for_release({"workflow_runs": runs}, SHA)), 4)

    def test_non_main_runs_are_rejected(self) -> None:
        runs = [run(name, branch="feature") for name in REQUIRED_WORKFLOWS]
        self.assertEqual(len(failures_for_release({"workflow_runs": runs}, SHA)), 4)

    def test_latest_failed_run_blocks_previous_success(self) -> None:
        runs = list(self.all_green["workflow_runs"])
        runs.append(
            run(
                "Backend Tests",
                conclusion="failure",
                timestamp="2026-10-12T16:30:00Z",
            )
        )
        self.assertEqual(
            failures_for_release({"workflow_runs": runs}, SHA),
            ["Backend Tests: conclusion='failure'"],
        )

    def test_pending_rerun_blocks_publication(self) -> None:
        runs = list(self.all_green["workflow_runs"])
        pending = run(
            "Backend Tests",
            status="in_progress",
            timestamp="2026-10-12T16:30:00Z",
        )
        runs.append(pending)
        self.assertEqual(
            failures_for_release({"workflow_runs": runs}, SHA),
            ["Backend Tests: not completed"],
        )

    def test_manual_dispatch_can_supply_a_green_gate(self) -> None:
        runs = [run(name, event="workflow_dispatch") for name in REQUIRED_WORKFLOWS]
        self.assertEqual(failures_for_release({"workflow_runs": runs}, SHA), [])

    def test_invalid_sha_fails_closed(self) -> None:
        self.assertTrue(failures_for_release(self.all_green, "abc"))
        self.assertTrue(failures_for_release(self.all_green, "A" * 40))

    def test_malformed_api_data_fails_closed(self) -> None:
        self.assertTrue(failures_for_release({}, SHA))


if __name__ == "__main__":
    unittest.main()
