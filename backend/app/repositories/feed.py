from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.models.feed import Feed
from app.repositories.base import BaseRepository


class FeedRepository(BaseRepository[Feed]):
    def __init__(self) -> None:
        super().__init__(Feed)

    def claim_due_active(
        self,
        db: Session,
        *,
        now: datetime,
        claim_expires_at: datetime,
        claimed_by: str,
        limit: int = 100,
    ) -> list[UUID]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        due_at = Feed.last_fetched_at + (
            Feed.fetch_interval_minutes * text("INTERVAL '1 minute'")
        )
        due_feed_ids = (
            select(Feed.id)
            .where(Feed.active.is_(True))
            .where(Feed.deleted_at.is_(None))
            .where((Feed.last_fetched_at.is_(None)) | (due_at <= now))
            .where((Feed.claim_expires_at.is_(None)) | (Feed.claim_expires_at <= now))
            .order_by(Feed.priority.asc(), Feed.last_fetched_at.asc().nullsfirst())
            .limit(limit)
            .with_for_update(skip_locked=True)
            .cte("due_feed_ids")
        )
        statement = (
            update(Feed)
            .where(Feed.id.in_(select(due_feed_ids.c.id)))
            .values(
                claimed_at=now,
                claimed_by=claimed_by,
                claim_expires_at=claim_expires_at,
            )
            .returning(Feed.id)
        )
        return list(db.scalars(statement).all())
