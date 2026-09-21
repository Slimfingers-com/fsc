from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session

from app.models.claim import ArticleClaim
from app.models.entity import ArticleEntity, Entity
from app.models.perspective import ArticlePerspective


class PerspectiveRepository:
    def load_active_claims(
        self,
        db: Session,
        *,
        article_ids: list[UUID],
        for_update: bool = False,
    ) -> dict[UUID, list[ArticleClaim]]:
        if not article_ids:
            return {}

        statement = (
            select(ArticleClaim)
            .where(
                ArticleClaim.article_id.in_(
                    article_ids
                ),
                ArticleClaim.deleted_at.is_(
                    None
                ),
            )
            .order_by(
                ArticleClaim.article_id,
                ArticleClaim.text_source,
                ArticleClaim.sentence_index,
                ArticleClaim.start_offset,
                ArticleClaim.id,
            )
        )

        if for_update:
            statement = (
                statement.with_for_update(
                    of=ArticleClaim
                )
                .execution_options(
                    populate_existing=True
                )
            )

        grouped: dict[
            UUID,
            list[ArticleClaim],
        ] = defaultdict(list)

        for claim in db.scalars(
            statement
        ).all():
            grouped[
                claim.article_id
            ].append(claim)

        return dict(grouped)

    def load_active_mentions(
        self,
        db: Session,
        *,
        article_ids: list[UUID],
        for_update: bool = False,
    ) -> dict[
        UUID,
        list[ArticleEntity],
    ]:
        if not article_ids:
            return {}

        statement = (
            select(ArticleEntity)
            .join(
                Entity,
                Entity.id
                == ArticleEntity.entity_id,
            )
            .where(
                ArticleEntity.article_id.in_(
                    article_ids
                ),
                ArticleEntity.deleted_at.is_(
                    None
                ),
                Entity.deleted_at.is_(
                    None
                ),
            )
            .order_by(
                ArticleEntity.article_id,
                ArticleEntity.text_source,
                ArticleEntity.sentence_index,
                ArticleEntity.start_offset,
                ArticleEntity.id,
            )
        )

        if for_update:
            statement = (
                statement.with_for_update(
                    of=ArticleEntity
                )
                .execution_options(
                    populate_existing=True
                )
            )

        grouped: dict[
            UUID,
            list[ArticleEntity],
        ] = defaultdict(list)

        for mention in db.scalars(
            statement
        ).all():
            grouped[
                mention.article_id
            ].append(mention)

        return dict(grouped)

    def deactivate_for_inactive_claims(
        self,
        db: Session,
        *,
        now: datetime,
    ) -> list[UUID]:
        active_claim = exists(
            select(
                ArticleClaim.id
            ).where(
                ArticleClaim.id
                == ArticlePerspective.claim_id,
                ArticleClaim.deleted_at.is_(
                    None
                ),
            )
        )

        article_ids = list(
            db.scalars(
                update(
                    ArticlePerspective
                )
                .where(
                    ArticlePerspective.deleted_at.is_(
                        None
                    ),
                    ~active_claim,
                )
                .values(
                    deleted_at=now,
                    updated_at=now,
                )
                .returning(
                    ArticlePerspective.article_id
                )
            ).all()
        )

        return list(
            dict.fromkeys(
                article_ids
            )
        )

    def replace_article_results(
        self,
        db: Session,
        *,
        article_id: UUID,
        now: datetime,
    ) -> None:
        db.execute(
            update(ArticlePerspective)
            .where(
                ArticlePerspective.article_id
                == article_id,
                ArticlePerspective.deleted_at.is_(
                    None
                ),
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )
        db.flush()
