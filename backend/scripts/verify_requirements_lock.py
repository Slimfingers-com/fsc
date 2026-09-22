from __future__ import annotations

import re
import sys
from pathlib import Path


_REQUIREMENT = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)"
    r"(?:\[[^\]]+\])?"
    r"==(?P<version>[^;\s]+)$"
)


def normalize_name(value: str) -> str:
    return re.sub(
        r"[-_.]+",
        "-",
        value,
    ).casefold()


def parse_exact_requirements(
    path: Path,
) -> dict[str, str]:
    result: dict[str, str] = {}

    for line_number, raw in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):
        line = raw.strip()
        if (
            not line
            or line.startswith("#")
        ):
            continue

        match = _REQUIREMENT.fullmatch(
            line
        )
        if match is None:
            raise ValueError(
                f"{path}:{line_number}: "
                "only exact == requirements "
                "are supported"
            )

        name = normalize_name(
            match.group("name")
        )
        version = match.group(
            "version"
        )
        result[name] = version

    return result


def verify(
    manifest: Path,
    lockfile: Path,
) -> None:
    direct = parse_exact_requirements(
        manifest
    )
    locked = parse_exact_requirements(
        lockfile
    )

    mismatches = [
        (
            name,
            version,
            locked.get(name),
        )
        for name, version
        in sorted(direct.items())
        if locked.get(name) != version
    ]

    if mismatches:
        details = "\n".join(
            (
                f"- {name}: "
                f"manifest={expected}, "
                f"lock={actual or 'missing'}"
            )
            for (
                name,
                expected,
                actual,
            ) in mismatches
        )
        raise ValueError(
            "requirements.lock is stale:\n"
            f"{details}"
        )


def main() -> int:
    manifest = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "requirements.txt"
    )
    lockfile = Path(
        sys.argv[2]
        if len(sys.argv) > 2
        else "requirements.lock"
    )

    try:
        verify(
            manifest,
            lockfile,
        )
    except ValueError as exc:
        print(
            str(exc),
            file=sys.stderr,
        )
        return 1

    print(
        "requirements.lock matches "
        "all direct requirements."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
