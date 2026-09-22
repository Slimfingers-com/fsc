from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SEMVER = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def read_version() -> str:
    version = Path("VERSION").read_text(
        encoding="utf-8"
    ).strip()
    if not SEMVER.fullmatch(version):
        raise ValueError(
            f"VERSION is not valid SemVer: {version!r}"
        )
    return version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag")
    args = parser.parse_args()

    version = read_version()

    package = json.loads(
        Path("frontend/package.json").read_text(
            encoding="utf-8"
        )
    )
    lock = json.loads(
        Path("frontend/package-lock.json").read_text(
            encoding="utf-8"
        )
    )

    mismatches: list[str] = []
    if package.get("version") != version:
        mismatches.append(
            "frontend/package.json version"
        )
    if lock.get("version") != version:
        mismatches.append(
            "frontend/package-lock.json version"
        )
    if (
        lock.get("packages", {})
        .get("", {})
        .get("version")
        != version
    ):
        mismatches.append(
            "frontend/package-lock.json root package version"
        )

    changelog = Path("CHANGELOG.md").read_text(
        encoding="utf-8"
    )
    if f"## [{version}]" not in changelog:
        mismatches.append(
            "CHANGELOG.md release heading"
        )

    notes = Path(
        f"docs/operations/release-{version}.md"
    )
    if not notes.is_file():
        mismatches.append(
            f"missing release notes: {notes}"
        )

    if args.tag is not None:
        expected = f"v{version}"
        if args.tag != expected:
            mismatches.append(
                f"tag {args.tag!r} != {expected!r}"
            )

    if mismatches:
        raise SystemExit(
            "Release metadata mismatch:\n- "
            + "\n- ".join(mismatches)
        )

    print(
        f"Release metadata is consistent for {version}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
