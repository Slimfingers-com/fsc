from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.claim import ArticleClaim
from app.models.claim_relation import StoryClaimGroup, StoryClaimGroupMember
from app.models.evidence import StoryClaimEvidence, StoryEvidence
from app.models.feed import Feed
from app.models.perspective import ArticlePerspective
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.perspectives.provider import PerspectiveKind


@dataclass(frozen=True, slots=True)
class EvidenceClaimRow:
    group: StoryClaimGroup
    member: StoryClaimGroupMember
    claim: ArticleClaim
    article: Article
    source: Source


class EvidenceRepository:
    @staticmethod
    def _eligible_conditions():
        return (
            Story.deleted_at.is_(None),
            StoryArticle.deleted_at.is_(None),
            Article.deleted_at.is_(None),
            Article.normalized_at.is_not(None),
            Article.normalized_text.is_not(None),
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            Source.deleted_at.is_(None),
            Source.active.is_(True),
            ArticleClaim.deleted_at.is_(None),
            StoryClaimGroup.deleted_at.is_(None),
            StoryClaimGroupMember.deleted_at.is_(None),
        )

    def list_candidate_stories(
        self,
        db: Session,
        *,
        after_created_at: datetime | None,
        after_id: UUID | None,
        limit: int,
    ) -> list[Story]:
        eligible_group = exists(
            select(StoryClaimGroup.id)
            .join(
                StoryClaimGroupMember,
                StoryClaimGroupMember.group_id == StoryClaimGroup.id,
            )
            .join(
                ArticleClaim,
                ArticleClaim.id == StoryClaimGroupMember.claim_id,
            )
            .join(Article, Article.id == ArticleClaim.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(Source, Source.id == Feed.source_id)
            .join(
                StoryArticle,
                and_(
                    StoryArticle.story_id == Story.id,
                    StoryArticle.article_id == Article.id,
                ),
            )
            .where(
                StoryClaimGroup.story_id == Story.id,
                *self._eligible_conditions(),
            )
        )
        conditions = [
            Story.deleted_at.is_(None),
            eligible_group,
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

    def load_claim_rows(
        self,
        db: Session,
        *,
        story_id: UUID,
        for_update: bool = False,
    ) -> list[EvidenceClaimRow]:
        statement = (
            select(
                StoryClaimGroup,
                StoryClaimGroupMember,
                ArticleClaim,
                Article,
                Source,
            )
            .join(
                StoryClaimGroupMember,
                StoryClaimGroupMember.group_id == StoryClaimGroup.id,
            )
            .join(
                ArticleClaim,
                ArticleClaim.id == StoryClaimGroupMember.claim_id,
            )
            .join(Article, Article.id == ArticleClaim.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(Source, Source.id == Feed.source_id)
            .join(
                StoryArticle,
                and_(
                    StoryArticle.story_id == StoryClaimGroup.story_id,
                    StoryArticle.article_id == Article.id,
                ),
            )
            .join(Story, Story.id == StoryClaimGroup.story_id)
            .where(
                StoryClaimGroup.story_id == story_id,
                *self._eligible_conditions(),
            )
            .order_by(
                StoryClaimGroup.id,
                Source.id,
                Article.id,
                ArticleClaim.id,
            )
        )
        if for_update:
            statement = statement.with_for_update(
                of=(
                    StoryClaimGroup,
                    StoryClaimGroupMember,
                )
            ).execution_options(populate_existing=True)

        return [
            EvidenceClaimRow(
                group=row[0],
                member=row[1],
                claim=row[2],
                article=row[3],
                source=row[4],
            )
            for row in db.execute(statement).all()
        ]


    def load_direct_quotes(
        self,
        db: Session,
        *,
        claim_ids: list[UUID],
    ) -> dict[UUID, tuple[str, ...]]:
        if not claim_ids:
            return {}

        rows = db.execute(
            select(
                ArticlePerspective.claim_id,
                ArticlePerspective.evidence_text,
            )
            .join(
                ArticleClaim,
                ArticleClaim.id == ArticlePerspective.claim_id,
            )
            .where(
                ArticlePerspective.claim_id.in_(claim_ids),
                ArticlePerspective.article_id == ArticleClaim.article_id,
                ArticlePerspective.deleted_at.is_(None),
                ArticleClaim.deleted_at.is_(None),
                ArticlePerspective.perspective_kind == PerspectiveKind.QUOTED,
            )
            .order_by(
                ArticlePerspective.claim_id,
                ArticlePerspective.id,
            )
        ).all()

        result: dict[UUID, list[str]] = {}
        for claim_id, evidence_text in rows:
            result.setdefault(
                claim_id,
                [],
            ).append(evidence_text)

        return {
            claim_id: tuple(values)
            for claim_id, values in result.items()
        }

    def replace_story_results(
        self,
        db: Session,
        *,
        story_id: UUID,
        now: datetime,
    ) -> None:
        db.execute(
            update(StoryClaimEvidence)
            .where(
                StoryClaimEvidence.story_id == story_id,
                StoryClaimEvidence.deleted_at.is_(None),
            )
            .values(deleted_at=now, updated_at=now)
        )
        db.execute(
            update(StoryEvidence)
            .where(
                StoryEvidence.story_id == story_id,
                StoryEvidence.deleted_at.is_(None),
            )
            .values(deleted_at=now, updated_at=now)
        )
        db.flush()

    def deactivate_without_active_groups(
        self,
        db: Session,
        *,
        now: datetime,
    ) -> list[UUID]:
        active_group = exists(
            select(StoryClaimGroup.id).where(
                StoryClaimGroup.story_id == StoryEvidence.story_id,
                StoryClaimGroup.deleted_at.is_(None),
            )
        )
        story_ids = list(
            db.scalars(
                select(StoryEvidence.story_id)
                .where(
                    StoryEvidence.deleted_at.is_(None),
                    ~active_group,
                )
                .distinct()
            ).all()
        )
        if not story_ids:
            return []

        db.execute(
            update(StoryClaimEvidence)
            .where(
                StoryClaimEvidence.story_id.in_(story_ids),
                StoryClaimEvidence.deleted_at.is_(None),
            )
            .values(deleted_at=now, updated_at=now)
        )
        db.execute(
            update(StoryEvidence)
            .where(
                StoryEvidence.story_id.in_(story_ids),
                StoryEvidence.deleted_at.is_(None),
            )
            .values(deleted_at=now, updated_at=now)
        )
        return story_ids
