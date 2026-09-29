import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.source_catalog_reconciliation import (
    SourceCatalogReconciler,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or apply reviewed source-catalog feed materialization. "
            "Dry-run is the default."
        )
    )
    parser.add_argument(
        "catalogs",
        nargs="+",
        help=(
            "Explicit catalog JSON paths. Only entries with reviewed "
            "configured feeds are materialized."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the planned changes in one transaction.",
    )
    return parser


def _resolve_catalog(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (BACKEND_ROOT / path).resolve()
    else:
        path = path.resolve()

    catalog_root = (BACKEND_ROOT / "catalog").resolve()
    if catalog_root not in path.parents:
        raise ValueError(
            f"Catalog path must be below {catalog_root}: {path}"
        )
    if path.suffix.lower() != ".json":
        raise ValueError(f"Catalog must be JSON: {path}")
    if not path.is_file():
        raise ValueError(f"Catalog does not exist: {path}")
    return path


def main() -> int:
    args = _parser().parse_args()
    reconciler = SourceCatalogReconciler()

    try:
        catalog_paths = [
            _resolve_catalog(value)
            for value in args.catalogs
        ]
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    reports = []
    with SessionLocal() as db:
        try:
            for path in catalog_paths:
                catalog = json.loads(path.read_text(encoding="utf-8"))
                report = reconciler.reconcile(
                    db,
                    catalog,
                    catalog_name=path.name,
                    apply=args.apply,
                )
                reports.append(report)

                if report.has_conflicts and args.apply:
                    raise RuntimeError(
                        f"{path.name} contains reconciliation conflicts"
                    )

            if args.apply:
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            raise

    payload = {
        "mode": "apply" if args.apply else "dry-run",
        "catalogs": [
            {
                "catalog": report.catalog_name,
                "change_count": report.change_count,
                "conflicts": list(report.conflicts),
                "actions": [
                    {
                        "action": action.action,
                        "source": action.source_name,
                        "feed": action.feed_name,
                        "detail": action.detail,
                    }
                    for action in report.actions
                ],
            }
            for report in reports
        ],
    }
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )

    return (
        1
        if any(report.has_conflicts for report in reports)
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
