from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.feed import Feed
from app.repositories.base import BaseRepository


class FeedRepository(BaseRepository[Feed]):
    def __init__(self) -> None:
        super().__init__(Feed)

    def list_due_active(
        self,
        db: Session,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[Feed]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        due_at = Feed.last_fetched_at + (
            Feed.fetch_interval_minutes * text("INTERVAL '1 minute'")
        )
        statement = (
            select(Feed)
            .where(Feed.active.is_(True))
            .where(Feed.deleted_at.is_(None))
            .where((Feed.last_fetched_at.is_(None)) | (due_at <= now))
            .order_by(Feed.priority.asc(), Feed.last_fetched_at.asc().nullsfirst())
            .limit(limit)
        )
        return list(db.scalars(statement).all())
