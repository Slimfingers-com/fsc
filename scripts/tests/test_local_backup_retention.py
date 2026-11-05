"""Fail-closed tests for automatic post-offsite local dump retention."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "infrastructure/backup/prune_local_backups.py"
spec = importlib.util.spec_from_file_location("fsc_local_retention", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
prune_local_backups = module.prune_local_backups

OLD = "fsc-20261102T021502Z.dump"
LATEST = "fsc-20261103T021502Z.dump"
MANUAL = "fsc-20261101-before-migration.dump"


class LocalBackupRetentionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.directory = Path(self.workspace.name)
        self.old = self.make_dump(OLD)
        self.latest = self.make_dump(LATEST)
        (self.directory / MANUAL).write_bytes(b"manual")
        (self.directory / "fsc-20261104T021502Z.dump.tmp.123").write_bytes(b"partial")
        (self.directory / "backup.log").write_text("retain logs")

    def make_dump(self, name: str) -> Path:
        path = self.directory / name
        payload = b"PGDMP" + name.encode("ascii")
        path.write_bytes(payload)
        checksum = hashlib.sha256(payload).hexdigest()
        (self.directory / (name + ".sha256")).write_text(
            f"{checksum}  {name}\n", encoding="ascii",
        )
        return path

    def test_dry_run_does_not_delete_anything(self) -> None:
        files = set(self.directory.iterdir())
        candidates = prune_local_backups(self.directory, self.latest)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(set(self.directory.iterdir()), files)

    def test_removes_old_dump_and_checksum_but_keeps_latest_and_manual(self) -> None:
        candidates = prune_local_backups(self.directory, self.latest, execute=True)
        self.assertEqual(len(candidates), 2)
        self.assertFalse(self.old.exists())
        self.assertFalse(Path(str(self.old) + ".sha256").exists())
        self.assertTrue(self.latest.exists())
        self.assertTrue(Path(str(self.latest) + ".sha256").exists())
        self.assertTrue((self.directory / MANUAL).exists())
        self.assertTrue((self.directory / "backup.log").exists())
        self.assertTrue((self.directory / "fsc-20261104T021502Z.dump.tmp.123").exists())

    def test_corrupt_latest_preserves_older_backups(self) -> None:
        self.latest.write_bytes(b"PGDMPcorrupt")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            prune_local_backups(self.directory, self.latest, execute=True)
        self.assertTrue(self.old.exists())

    def test_invalid_backup_format_fails_closed(self) -> None:
        self.latest.write_bytes(b"not a pg dump")
        with self.assertRaisesRegex(ValueError, "PostgreSQL"):
            prune_local_backups(self.directory, self.latest, execute=True)
        self.assertTrue(self.old.exists())

    def test_kept_backup_outside_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            external = Path(other) / LATEST
            external.write_bytes(b"PGDMPexternal")
            with self.assertRaisesRegex(ValueError, "directly inside"):
                prune_local_backups(self.directory, external, execute=True)
        self.assertTrue(self.old.exists())

    def test_old_checksum_symlink_causes_abort_without_deletion(self) -> None:
        sidecar = Path(str(self.old) + ".sha256")
        sidecar.unlink()
        sidecar.symlink_to(self.latest)
        with self.assertRaisesRegex(ValueError, "unsafe old checksum"):
            prune_local_backups(self.directory, self.latest, execute=True)
        self.assertTrue(self.old.exists())


if __name__ == "__main__":
    unittest.main()
