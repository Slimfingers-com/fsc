from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.orm import Session


def expected_database_heads(
    alembic_ini: str | Path = "alembic.ini",
) -> set[str]:
    config = Config(
        str(alembic_ini)
    )
    script = ScriptDirectory.from_config(
        config
    )
    return set(
        script.get_heads()
    )


def current_database_heads(
    db: Session,
) -> set[str]:
    return set(
        db.scalars(
            text(
                "SELECT version_num "
                "FROM alembic_version"
            )
        ).all()
    )


def database_schema_is_current(
    db: Session,
) -> bool:
    return (
        current_database_heads(db)
        == expected_database_heads()
    )
