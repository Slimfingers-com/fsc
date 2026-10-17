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

    def test_publisher_has_only_manual_dispatch_trigger(self) -> None:
        workflow = (
            Path(__file__).resolve().parents[2]
            / ".github/workflows/publish-release.yml"
        ).read_text(encoding="utf-8")
        event_block = workflow.split("\non:\n", 1)[1].split(
            "\npermissions:", 1
        )[0]
        self.assertIn("  workflow_dispatch:", event_block)
        self.assertNotIn("  workflow_run:", event_block)
        self.assertNotIn("  push:", event_block)
        self.assertNotIn("  release:", event_block)

    def test_manual_publication_gates_include_issue_and_confirmation(self) -> None:
        workflow = (
            Path(__file__).resolve().parents[2]
            / ".github/workflows/publish-release.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("PUBLISH FSC $RELEASE_VERSION", workflow)
        self.assertIn("/issues/29", workflow)
        self.assertIn("environment: release-publication", workflow)

        self.assertIn(
            "needs: [preflight, backend_ci, frontend_ci, fullstack_ci, metadata_ci]",
            workflow,
        )
        for name in ("backend", "frontend", "full-stack-e2e", "release-metadata"):
            self.assertIn(
                f"uses: ./.github/workflows/{name}-tests.yml"
                if name in ("backend", "frontend")
                else f"uses: ./.github/workflows/{name}.yml",
                workflow,
            )

    def test_reusable_release_checks_are_supported_by_all_suites(self) -> None:
        root = Path(__file__).resolve().parents[2] / ".github/workflows"
        for name in (
            "backend-tests.yml",
            "frontend-tests.yml",
            "full-stack-e2e.yml",
            "release-metadata.yml",
        ):
            source = (root / name).read_text(encoding="utf-8")
            self.assertIn("on:\n  workflow_call:\n", source)


    def test_no_obsolete_automatic_publisher_can_run(self) -> None:
        workflows = Path(__file__).resolve().parents[2] / ".github/workflows"
        self.assertFalse(
            (workflows / "promote-release-candidate.yml").exists(),
            "Automatic release-candidate promotion must stay disabled.",
        )
        release_creators = [
            path.name
            for path in sorted(workflows.glob("*.yml"))
            if "gh release create" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(
            release_creators, ["publish-release.yml"],
            "Only the explicitly approved manual workflow may publish releases.",
        )


if __name__ == "__main__":
    unittest.main()
