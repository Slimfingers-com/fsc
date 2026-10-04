import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.enums.source_dependency import SourceRelationKind
from app.models.source import Source
from app.models.source_dependency import SourceRelation


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Dry-run/apply reviewed static source-independence relations."
    )
    p.add_argument("catalog")
    p.add_argument("--apply", action="store_true")
    return p


def resolve_catalog(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (BACKEND_ROOT / path).resolve()
    root = (BACKEND_ROOT / "catalog").resolve()
    if root not in path.parents or path.suffix.lower() != ".json":
        raise ValueError("catalog must be a JSON file below backend/catalog")
    return path


def main() -> int:
    args = parser().parse_args()
    path = resolve_catalog(args.catalog)
    catalog = json.loads(path.read_text(encoding="utf-8"))
    kind = SourceRelationKind(catalog["relation_kind"])

    planned = []
    with SessionLocal() as db:
        sources = {
            row.slug: row
            for row in db.scalars(
                select(Source).where(Source.deleted_at.is_(None), Source.active.is_(True))
            )
        }
        for family in catalog["families"]:
            parent_slug = family["parent"]
            if parent_slug not in sources:
                raise RuntimeError(f"missing active parent source: {parent_slug}")
            for member_slug in family["members"]:
                if member_slug not in sources:
                    raise RuntimeError(f"missing active member source: {member_slug}")
                parent = sources[parent_slug]
                member = sources[member_slug]
                existing = db.scalar(
                    select(SourceRelation).where(
                        SourceRelation.deleted_at.is_(None),
                        SourceRelation.source_id == parent.id,
                        SourceRelation.related_source_id == member.id,
                        SourceRelation.relation_kind == kind,
                        SourceRelation.valid_from.is_(None),
                        SourceRelation.valid_to.is_(None),
                    )
                )
                if existing is not None:
                    planned.append({"action": "no_change", "parent": parent_slug, "member": member_slug})
                    continue
                planned.append({"action": "create_relation", "parent": parent_slug, "member": member_slug})
                if args.apply:
                    db.add(
                        SourceRelation(
                            source_id=parent.id,
                            related_source_id=member.id,
                            relation_kind=kind,
                            notes=catalog.get("notes"),
                        )
                    )
        if args.apply:
            db.commit()
        else:
            db.rollback()

    print(json.dumps({
        "mode": "apply" if args.apply else "dry-run",
        "catalog": path.name,
        "relation_kind": kind.value,
        "change_count": sum(1 for row in planned if row["action"] == "create_relation"),
        "actions": planned,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
