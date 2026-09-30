import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.agency_provenance_backfill import (
    AgencyProvenanceBackfiller,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or apply historical agency-provenance candidates from "
            "stored article bylines. Dry-run is the default."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the planned pending provenance candidates.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    backfiller = AgencyProvenanceBackfiller()

    with SessionLocal() as db:
        try:
            report = backfiller.backfill(db)
            if args.apply:
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            raise

    payload = {
        "mode": "apply" if args.apply else "dry-run",
        "scanned_articles": report.scanned_articles,
        "detected_candidates": report.detected_candidates,
        "change_count": report.change_count,
        "already_present": report.already_present,
        "missing_upstream_source": report.missing_upstream_source,
        "self_dependencies_skipped": report.self_dependencies_skipped,
        "changes_by_source": report.changes_by_source,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
