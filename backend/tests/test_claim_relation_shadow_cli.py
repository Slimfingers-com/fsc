import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_luna_shadow_cli_help_is_runnable():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_claim_relation_shadow.py",
            "--help",
        ],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "shadow mode" in completed.stdout.casefold()
