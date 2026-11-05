#!/usr/bin/env python3
"""Keep only the verified current scheduled database dump after offsite success.

This is a local retention helper, NOT an offsite pruning operation.
Default is a read-only dry run. The caller must hold the nightly backup lock
and invoke --execute only AFTER offsite upload and repository verification.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

BACKUP_FILENAME = re.compile(r"fsc-\d{8}T\d{6}Z\.dump\Z")
CHECKSUM_LINE = re.compile(r"([0-9a-f]{64})  (fsc-\d{8}T\d{6}Z\.dump)\n?\Z")


def _regular_file(path: Path) -> bool:
    return not path.is_symlink() and path.is_file()


def prune_local_backups(directory: Path, keep: Path, *, execute: bool = False) -> list[Path]:
    """List or remove older scheduled backups and matching checksums.

    Never remove the requested kept backup, unexpected/manual filenames,
    partial .tmp dumps, backup logs, or any offsite snapshots.
    """
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("backup directory must be a real directory")

    directory = directory.resolve(strict=True)
    if not keep.is_absolute() or keep.parent != directory:
        raise ValueError("kept backup must be directly inside the backup directory")
    if not BACKUP_FILENAME.fullmatch(keep.name) or not _regular_file(keep):
        raise ValueError("kept backup must be an existing regular scheduled dump")
    checksum_path = directory / (keep.name + ".sha256")
    if not _regular_file(checksum_path):
        raise ValueError("kept backup checksum missing or unsafe")

    match = CHECKSUM_LINE.fullmatch(checksum_path.read_text(encoding="ascii"))
    if match is None or match.group(2) != keep.name:
        raise ValueError("kept backup checksum file malformed")
    digest = hashlib.sha256()
    with keep.open("rb") as stream:
        if stream.read(5) != b"PGDMP":
            raise ValueError("kept backup is not a PostgreSQL custom-format dump")
        stream.seek(0)
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != match.group(1):
        raise ValueError("kept backup failed SHA-256 validation")

    to_delete: list[Path] = []
    for path in sorted(directory.iterdir()):
        if not BACKUP_FILENAME.fullmatch(path.name) or path == keep:
            continue
        if not _regular_file(path):
            raise ValueError(f"unsafe old backup entry: {path.name}")
        sidecar = directory / (path.name + ".sha256")
        if sidecar.exists() or sidecar.is_symlink():
            if not _regular_file(sidecar):
                raise ValueError(f"unsafe old checksum entry: {sidecar.name}")
            to_delete.append(sidecar)
        to_delete.append(path)

    if execute:
        for path in to_delete:
            path.unlink()

    return to_delete


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--keep", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    candidates = prune_local_backups(
        args.directory, args.keep, execute=args.execute,
    )
    action = "Removed" if args.execute else "Would remove"
    for path in candidates:
        print(f"{action}: {path.name}")
    print(f"Local retention: kept {args.keep.name}; {len(candidates)} old files "
          f"{'removed' if args.execute else 'eligible for removal'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
