from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.claim import ArticleClaim


class ClaimRepository:
    def replace_article_results(
        self,
        db: Session,
        *,
        article_id: UUID,
        now: datetime,
    ) -> None:
        db.execute(
            update(ArticleClaim)
            .where(
                ArticleClaim.article_id
                == article_id,
                ArticleClaim.deleted_at.is_(
                    None
                ),
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )

        db.flush()

    def list_active_for_article(
        self,
        db: Session,
        article_id: UUID,
    ) -> list[ArticleClaim]:
        return list(
            db.scalars(
                select(ArticleClaim)
                .where(
                    ArticleClaim.article_id
                    == article_id,
                    ArticleClaim.deleted_at.is_(
                        None
                    ),
                )
                .order_by(
                    ArticleClaim.text_source,
                    ArticleClaim.sentence_index,
                    ArticleClaim.start_offset,
                    ArticleClaim.id,
                )
            ).all()
        )

    def get_active(
        self,
        db: Session,
        claim_id: UUID,
    ) -> ArticleClaim | None:
        return db.scalar(
            select(ArticleClaim).where(
                ArticleClaim.id
                == claim_id,
                ArticleClaim.deleted_at.is_(
                    None
                ),
            )
        )
