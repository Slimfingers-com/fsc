import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.legacy_source_identity_reconciliation import (
    LegacySourceIdentityReconciler,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or apply canonicalization of known legacy Source "
            "identities. Dry-run is the default."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist all planned identity changes in one transaction.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    reconciler = LegacySourceIdentityReconciler()

    with SessionLocal() as db:
        try:
            report = reconciler.reconcile(
                db,
                apply=args.apply,
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
        "change_count": report.change_count,
        "conflicts": list(report.conflicts),
        "actions": [
            {
                "action": action.action,
                "slug": action.slug,
                "detail": action.detail,
            }
            for action in report.actions
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if report.has_conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
