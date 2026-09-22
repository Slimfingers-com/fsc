from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.consensus import (
    StoryConsensusSummary,
    StoryDifferenceSummary,
)
from app.models.coverage import (
    StoryCoverageGap,
    StoryCoverageSummary,
    StoryMissingPerspective,
)
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle


@dataclass(frozen=True, slots=True)
class CoverageSourceRow:
    membership: StoryArticle
    article: Article
    source: Source


class CoverageRepository:
    @staticmethod
    def _eligible_source_conditions():
        return (
            StoryArticle.deleted_at.is_(None),
            Article.deleted_at.is_(None),
            Article.normalized_at.is_not(None),
            Article.normalized_text.is_not(None),
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            Source.deleted_at.is_(None),
            Source.active.is_(True),
        )

    def list_candidate_stories(
        self,
        db: Session,
        *,
        after_created_at: datetime | None,
        after_id: UUID | None,
        limit: int,
    ) -> list[Story]:
        active_consensus = exists(
            select(StoryConsensusSummary.id).where(
                StoryConsensusSummary.story_id == Story.id,
                StoryConsensusSummary.deleted_at.is_(None),
            )
        )
        conditions = [
            Story.deleted_at.is_(None),
            active_consensus,
        ]
        if after_created_at is not None and after_id is not None:
            conditions.append(
                or_(
                    Story.created_at > after_created_at,
                    and_(
                        Story.created_at == after_created_at,
                        Story.id > after_id,
                    ),
                )
            )
        return list(
            db.scalars(
                select(Story)
                .where(*conditions)
                .order_by(Story.created_at, Story.id)
                .limit(limit)
            ).all()
        )

    def load_source_rows(
        self,
        db: Session,
        *,
        story_id: UUID,
        for_update: bool = False,
    ) -> list[CoverageSourceRow]:
        statement = (
            select(
                StoryArticle,
                Article,
                Source,
            )
            .join(
                Article,
                Article.id == StoryArticle.article_id,
            )
            .join(
                Feed,
                Feed.id == Article.feed_id,
            )
            .join(
                Source,
                Source.id == Feed.source_id,
            )
            .where(
                StoryArticle.story_id == story_id,
                *self._eligible_source_conditions(),
            )
            .order_by(
                StoryArticle.article_time,
                StoryArticle.article_id,
                StoryArticle.id,
            )
        )
        if for_update:
            statement = statement.with_for_update(
                of=StoryArticle
            ).execution_options(
                populate_existing=True
            )
        return [
            CoverageSourceRow(
                membership=row[0],
                article=row[1],
                source=row[2],
            )
            for row in db.execute(statement).all()
        ]

    def load_consensus_summaries(
        self,
        db: Session,
        *,
        story_id: UUID,
        for_update: bool = False,
    ) -> list[StoryConsensusSummary]:
        statement = (
            select(StoryConsensusSummary)
            .where(
                StoryConsensusSummary.story_id == story_id,
                StoryConsensusSummary.deleted_at.is_(None),
            )
            .order_by(
                StoryConsensusSummary.claim_group_id
            )
        )
        if for_update:
            statement = statement.with_for_update(
                of=StoryConsensusSummary
            ).execution_options(
                populate_existing=True
            )
        return list(
            db.scalars(statement).all()
        )

    def load_difference_summaries(
        self,
        db: Session,
        *,
        story_id: UUID,
        for_update: bool = False,
    ) -> list[StoryDifferenceSummary]:
        statement = (
            select(StoryDifferenceSummary)
            .where(
                StoryDifferenceSummary.story_id == story_id,
                StoryDifferenceSummary.deleted_at.is_(None),
            )
            .order_by(
                StoryDifferenceSummary.claim_relation_id
            )
        )
        if for_update:
            statement = statement.with_for_update(
                of=StoryDifferenceSummary
            ).execution_options(
                populate_existing=True
            )
        return list(
            db.scalars(statement).all()
        )

    def replace_story_results(
        self,
        db: Session,
        *,
        story_id: UUID,
        now: datetime,
    ) -> None:
        db.execute(
            update(StoryMissingPerspective)
            .where(
                StoryMissingPerspective.story_id == story_id,
                StoryMissingPerspective.deleted_at.is_(None),
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )
        db.execute(
            update(StoryCoverageGap)
            .where(
                StoryCoverageGap.story_id == story_id,
                StoryCoverageGap.deleted_at.is_(None),
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )
        db.execute(
            update(StoryCoverageSummary)
            .where(
                StoryCoverageSummary.story_id == story_id,
                StoryCoverageSummary.deleted_at.is_(None),
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )
        db.flush()

    def deactivate_without_active_consensus(
        self,
        db: Session,
        *,
        now: datetime,
    ) -> list[UUID]:
        active_consensus = exists(
            select(StoryConsensusSummary.id).where(
                StoryConsensusSummary.story_id
                == StoryCoverageSummary.story_id,
                StoryConsensusSummary.deleted_at.is_(None),
            )
        )
        story_ids = list(
            db.scalars(
                select(
                    StoryCoverageSummary.story_id
                )
                .where(
                    StoryCoverageSummary.deleted_at.is_(None),
                    ~active_consensus,
                )
                .distinct()
            ).all()
        )
        if not story_ids:
            return []

        db.execute(
            update(StoryMissingPerspective)
            .where(
                StoryMissingPerspective.story_id.in_(
                    story_ids
                ),
                StoryMissingPerspective.deleted_at.is_(None),
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )
        db.execute(
            update(StoryCoverageGap)
            .where(
                StoryCoverageGap.story_id.in_(story_ids),
                StoryCoverageGap.deleted_at.is_(None),
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )
        db.execute(
            update(StoryCoverageSummary)
            .where(
                StoryCoverageSummary.story_id.in_(story_ids),
                StoryCoverageSummary.deleted_at.is_(None),
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )
        return story_ids
