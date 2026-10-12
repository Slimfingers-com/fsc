from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.claim import ArticleClaim
from app.models.claim_relation import StoryClaimGroup, StoryClaimRelation
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.models.story_processing import StoryProcessingState


@dataclass(frozen=True, slots=True)
class EligibleStoryMembership:
    membership: StoryArticle
    article: Article
    source_id: UUID


class ClaimRelationRepository:
    @staticmethod
    def _eligible_membership_conditions():
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
        processed: bool | None = None,
        now: datetime | None = None,
        pipeline: str = "claim_relations",
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
        excluded_story_ids: set[UUID] | None = None,
    ) -> list[Story]:
        eligible_claim = exists(
            select(ArticleClaim.id)
            .select_from(StoryArticle)
            .join(Article, Article.id == StoryArticle.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(Source, Source.id == Feed.source_id)
            .join(ArticleClaim, ArticleClaim.article_id == Article.id)
            .where(
                StoryArticle.story_id == Story.id,
                *self._eligible_membership_conditions(),
                ArticleClaim.deleted_at.is_(None),
            )
        )
        conditions = [Story.deleted_at.is_(None), eligible_claim]
        if excluded_story_ids:
            conditions.append(Story.id.not_in(excluded_story_ids))

        query = select(Story)
        if processed is not None:
            if (
                now is None
                or provider is None
                or provider_version is None
                or configuration_version is None
            ):
                raise ValueError(
                    "state-prefilter requires now and provider identity"
                )
            state = StoryProcessingState
            query = query.outerjoin(
                state,
                and_(
                    state.story_id == Story.id,
                    state.pipeline == pipeline,
                    state.deleted_at.is_(None),
                ),
            )
            conditions.extend(
                [
                    or_(
                        state.retry_after.is_(None),
                        state.retry_after <= now,
                    ),
                    or_(
                        state.claim_expires_at.is_(None),
                        state.claim_expires_at <= now,
                    ),
                ]
            )
            if processed:
                # SQL prefilter only. The exact snapshot hash and
                # atomic claim gate remain authoritative.
                membership_changed = exists(
                    select(StoryArticle.id)
                    .where(
                        StoryArticle.story_id == Story.id,
                        or_(
                            StoryArticle.created_at > state.last_processed_at,
                            StoryArticle.updated_at > state.last_processed_at,
                            StoryArticle.deleted_at > state.last_processed_at,
                        ),
                    )
                    .correlate(Story, state)
                )
                claim_changed = exists(
                    select(ArticleClaim.id)
                    .select_from(StoryArticle)
                    .join(
                        ArticleClaim,
                        ArticleClaim.article_id == StoryArticle.article_id,
                    )
                    .where(
                        StoryArticle.story_id == Story.id,
                        StoryArticle.deleted_at.is_(None),
                        or_(
                            ArticleClaim.created_at > state.last_processed_at,
                            ArticleClaim.updated_at > state.last_processed_at,
                            ArticleClaim.deleted_at > state.last_processed_at,
                            ArticleClaim.semantic_embedded_at
                            > state.last_processed_at,
                        ),
                    )
                    .correlate(Story, state)
                )
                article_or_feed_changed = exists(
                    select(Article.id)
                    .select_from(StoryArticle)
                    .join(Article, Article.id == StoryArticle.article_id)
                    .join(Feed, Feed.id == Article.feed_id)
                    .where(
                        StoryArticle.story_id == Story.id,
                        StoryArticle.deleted_at.is_(None),
                        or_(
                            Article.updated_at > state.last_processed_at,
                            Feed.updated_at > state.last_processed_at,
                        ),
                    )
                    .correlate(Story, state)
                )
                conditions.extend(
                    [
                        state.processed_input_hash.is_not(None),
                        or_(
                            state.processed_provider.is_distinct_from(provider),
                            state.processed_provider_version.is_distinct_from(
                                provider_version
                            ),
                            state.processed_configuration_version.is_distinct_from(
                                configuration_version
                            ),
                            Story.updated_at > state.last_processed_at,
                            membership_changed,
                            claim_changed,
                            article_or_feed_changed,
                        ),
                    ]
                )
            else:
                conditions.append(
                    or_(
                        state.id.is_(None),
                        state.processed_input_hash.is_(None),
                    )
                )

        if after_created_at is not None and after_id is not None:
            if processed is False:
                conditions.append(
                    or_(
                        Story.created_at < after_created_at,
                        and_(
                            Story.created_at == after_created_at,
                            Story.id < after_id,
                        ),
                    )
                )
            else:
                conditions.append(
                    or_(
                        Story.created_at > after_created_at,
                        and_(
                            Story.created_at == after_created_at,
                            Story.id > after_id,
                        ),
                    )
                )
        order_by = (
            (Story.created_at.desc(), Story.id.desc())
            if processed is False
            else (Story.created_at, Story.id)
        )
        return list(
            db.scalars(
                query.where(*conditions).order_by(*order_by).limit(limit)
            ).all()
        )

    def get_story(
        self,
        db: Session,
        *,
        story_id: UUID,
        for_update: bool = False,
    ) -> Story | None:
        statement = select(Story).where(
            Story.id == story_id,
            Story.deleted_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update(
                of=Story,
                key_share=True,
            ).execution_options(
                populate_existing=True
            )
        return db.scalar(statement)

    def load_eligible_memberships(
        self,
        db: Session,
        *,
        story_id: UUID,
        for_update: bool = False,
    ) -> list[EligibleStoryMembership]:
        statement = (
            select(StoryArticle, Article, Source.id.label("source_id"))
            .join(Article, Article.id == StoryArticle.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(Source, Source.id == Feed.source_id)
            .where(
                StoryArticle.story_id == story_id,
                *self._eligible_membership_conditions(),
            )
            .order_by(
                StoryArticle.article_time,
                StoryArticle.article_id,
                StoryArticle.id,
            )
        )
        if for_update:
            statement = statement.with_for_update(of=StoryArticle).execution_options(
                populate_existing=True
            )
        return [
            EligibleStoryMembership(
                membership=row[0],
                article=row[1],
                source_id=row.source_id,
            )
            for row in db.execute(statement).all()
        ]

    def lock_articles(self, db: Session, *, article_ids: list[UUID]) -> None:
        if not article_ids:
            return
        list(
            db.scalars(
                select(Article)
                .where(Article.id.in_(article_ids))
                .order_by(Article.id)
                .with_for_update(of=Article, key_share=True)
                .execution_options(populate_existing=True)
            ).all()
        )

    def load_active_claims(
        self,
        db: Session,
        *,
        article_ids: list[UUID],
        for_update: bool = False,
    ) -> list[ArticleClaim]:
        if not article_ids:
            return []
        statement = (
            select(ArticleClaim)
            .where(
                ArticleClaim.article_id.in_(article_ids),
                ArticleClaim.deleted_at.is_(None),
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
            statement = statement.with_for_update(of=ArticleClaim).execution_options(
                populate_existing=True
            )
        return list(db.scalars(statement).all())

    def replace_story_results(
        self,
        db: Session,
        *,
        story_id: UUID,
        now: datetime,
    ) -> None:
        db.execute(
            update(StoryClaimRelation)
            .where(
                StoryClaimRelation.story_id == story_id,
                StoryClaimRelation.deleted_at.is_(None),
            )
            .values(deleted_at=now, updated_at=now)
        )
        db.execute(
            update(StoryClaimGroup)
            .where(
                StoryClaimGroup.story_id == story_id,
                StoryClaimGroup.deleted_at.is_(None),
            )
            .values(deleted_at=now, updated_at=now)
        )
        db.flush()

    def deactivate_ineligible_results(
        self,
        db: Session,
        *,
        now: datetime,
    ) -> list[UUID]:
        eligible_claim = exists(
            select(ArticleClaim.id)
            .select_from(StoryArticle)
            .join(Article, Article.id == StoryArticle.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(Source, Source.id == Feed.source_id)
            .join(ArticleClaim, ArticleClaim.article_id == Article.id)
            .join(Story, Story.id == StoryArticle.story_id)
            .where(
                StoryArticle.story_id == StoryClaimGroup.story_id,
                Story.deleted_at.is_(None),
                *self._eligible_membership_conditions(),
                ArticleClaim.deleted_at.is_(None),
            )
        )
        story_ids = list(
            db.scalars(
                select(StoryClaimGroup.story_id)
                .where(
                    StoryClaimGroup.deleted_at.is_(None),
                    ~eligible_claim,
                )
                .distinct()
            ).all()
        )
        if not story_ids:
            return []

        db.execute(
            update(StoryClaimRelation)
            .where(
                StoryClaimRelation.story_id.in_(story_ids),
                StoryClaimRelation.deleted_at.is_(None),
            )
            .values(deleted_at=now, updated_at=now)
        )
        db.execute(
            update(StoryClaimGroup)
            .where(
                StoryClaimGroup.story_id.in_(story_ids),
                StoryClaimGroup.deleted_at.is_(None),
            )
            .values(deleted_at=now, updated_at=now)
        )
        return story_ids
