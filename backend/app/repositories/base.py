from datetime import UTC, datetime
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import BaseModel


ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Gemeinsame Datenzugriffe für FSC-Kernobjekte."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    def get_by_id(
        self,
        db: Session,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> ModelType | None:
        statement = select(self.model).where(self.model.id == entity_id)

        if not include_deleted:
            statement = statement.where(self.model.deleted_at.is_(None))

        return db.scalar(statement)

    def add(
        self,
        db: Session,
        entity: ModelType,
    ) -> ModelType:
        db.add(entity)
        return entity

    def flush(
        self,
        db: Session,
    ) -> None:
        db.flush()

    def soft_delete(
        self,
        entity: ModelType,
    ) -> None:
        entity.deleted_at = datetime.now(UTC)
