import hashlib
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import exists, func, or_, select, text, update
from sqlalchemy.orm import Session

from app.clustering.provider import (
    StoryCandidate,
    StoryClusteringInput,
)
from app.models.article import Article
from app.models.entity import ArticleEntity, Entity
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.models.topic import ArticleTopic, Topic


class StoryRepository:
    CLUSTERING_LOCK_KEY = 0x46534353544F5259

    @staticmethod
    def clustering_partition_lock_key(
        language_code: str | None,
    ) -> int:
        partition = (
            language_code
            if language_code is not None
            else "<none>"
        )
        digest = hashlib.sha256(
            (
                "fsc:story-clustering:"
                + partition
            ).encode("utf-8")
        ).digest()

        return int.from_bytes(
            digest[:8],
            "big",
            signed=True,
        )

    def acquire_processing_coordination_lock(
        self,
        db: Session,
    ) -> None:
        db.execute(
            text(
                "SELECT "
                "pg_advisory_xact_lock_shared(:lock_key)"
            ),
            {
                "lock_key": self.CLUSTERING_LOCK_KEY,
            },
        )

    def acquire_cleanup_lock(
        self,
        db: Session,
    ) -> None:
        db.execute(
            text(
                "SELECT pg_advisory_xact_lock(:lock_key)"
            ),
            {
                "lock_key": self.CLUSTERING_LOCK_KEY,
            },
        )

    def acquire_clustering_lock(
        self,
        db: Session,
        *,
        language_code: str | None,
    ) -> None:
        db.execute(
            text(
                "SELECT pg_advisory_xact_lock(:lock_key)"
            ),
            {
                "lock_key": (
                    self.clustering_partition_lock_key(
                        language_code
                    )
                ),
            },
        )

    def get_clustering_language(
        self,
        db: Session,
        article_id: UUID,
    ) -> tuple[bool, str | None]:
        row = db.execute(
            select(
                Article.language_code
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
                Article.id == article_id,
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Article.normalized_text.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
        ).one_or_none()

        if row is None:
            return False, None

        return True, row[0]

    def get_story(
        self,
        db: Session,
        story_id: UUID,
        *,
        for_update: bool = False,
    ) -> Story | None:
        statement = select(Story).where(
            Story.id == story_id,
            Story.deleted_at.is_(None),
        )

        if for_update:
            statement = statement.with_for_update(
                of=Story
            )

        return db.scalar(statement)

    def get_active_membership(
        self,
        db: Session,
        article_id: UUID,
        *,
        for_update: bool = False,
    ) -> StoryArticle | None:
        statement = (
            select(StoryArticle)
            .join(
                Story,
                Story.id == StoryArticle.story_id,
            )
            .where(
                StoryArticle.article_id == article_id,
                StoryArticle.deleted_at.is_(None),
                Story.deleted_at.is_(None),
            )
        )

        if for_update:
            statement = statement.with_for_update(
                of=StoryArticle
            )

        return db.scalar(statement)

    def get_membership_by_processing_run(
        self,
        db: Session,
        processing_run_id: UUID,
    ) -> StoryArticle | None:
        return db.scalar(
            select(StoryArticle).where(
                StoryArticle.processing_run_id
                == processing_run_id,
            )
        )

    def load_feature_ids(
        self,
        db: Session,
        article_ids: list[UUID],
    ) -> tuple[
        dict[UUID, tuple[UUID, ...]],
        dict[UUID, tuple[UUID, ...]],
    ]:
        if not article_ids:
            return {}, {}

        entity_sets: dict[
            UUID,
            set[UUID],
        ] = {
            article_id: set()
            for article_id in article_ids
        }

        topic_sets: dict[
            UUID,
            set[UUID],
        ] = {
            article_id: set()
            for article_id in article_ids
        }

        entity_rows = db.execute(
            select(
                ArticleEntity.article_id,
                ArticleEntity.entity_id,
            )
            .join(
                Entity,
                Entity.id == ArticleEntity.entity_id,
            )
            .where(
                ArticleEntity.article_id.in_(
                    article_ids
                ),
                ArticleEntity.deleted_at.is_(None),
                Entity.deleted_at.is_(None),
            )
        )

        for article_id, entity_id in entity_rows:
            entity_sets[
                article_id
            ].add(entity_id)

        topic_rows = db.execute(
            select(
                ArticleTopic.article_id,
                ArticleTopic.topic_id,
            )
            .join(
                Topic,
                Topic.id == ArticleTopic.topic_id,
            )
            .where(
                ArticleTopic.article_id.in_(
                    article_ids
                ),
                ArticleTopic.deleted_at.is_(None),
                Topic.deleted_at.is_(None),
            )
        )

        for article_id, topic_id in topic_rows:
            topic_sets[
                article_id
            ].add(topic_id)

        entity_ids = {
            article_id: tuple(
                sorted(
                    values,
                    key=str,
                )
            )
            for article_id, values
            in entity_sets.items()
        }

        topic_ids = {
            article_id: tuple(
                sorted(
                    values,
                    key=str,
                )
            )
            for article_id, values
            in topic_sets.items()
        }

        return entity_ids, topic_ids

    def list_candidates(
        self,
        db: Session,
        *,
        article: StoryClusteringInput,
        window_hours: float,
        limit: int,
    ) -> tuple[StoryCandidate, ...]:
        if window_hours <= 0:
            raise ValueError(
                "window_hours must be greater than zero"
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        overlap_conditions = []

        if article.title_terms:
            overlap_conditions.append(
                StoryArticle.title_terms.overlap(
                    list(article.title_terms)
                )
            )

        if article.entity_ids:
            overlap_conditions.append(
                StoryArticle.entity_ids.overlap(
                    list(article.entity_ids)
                )
            )

        if article.topic_ids:
            overlap_conditions.append(
                StoryArticle.topic_ids.overlap(
                    list(article.topic_ids)
                )
            )

        if not overlap_conditions:
            return ()

        window = timedelta(
            hours=window_hours
        )

        if article.language_code is None:
            language_condition = (
                Story.language_code.is_(None)
            )
        else:
            language_condition = (
                Story.language_code
                == article.language_code
            )

        ranked_candidates = (
            select(
                StoryArticle.id.label(
                    "membership_id"
                ),
                StoryArticle.article_time.label(
                    "article_time"
                ),
                func.row_number()
                .over(
                    partition_by=StoryArticle.story_id,
                    order_by=(
                        StoryArticle.article_time.desc(),
                        StoryArticle.id,
                    ),
                )
                .label("story_rank"),
            )
            .join(
                Story,
                Story.id
                == StoryArticle.story_id,
            )
            .join(
                Article,
                Article.id
                == StoryArticle.article_id,
            )
            .join(
                Feed,
                Feed.id
                == Article.feed_id,
            )
            .join(
                Source,
                Source.id
                == Feed.source_id,
            )
            .where(
                StoryArticle.deleted_at.is_(None),
                Story.deleted_at.is_(None),
                language_condition,
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Article.normalized_text.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
                StoryArticle.article_id
                != article.article_id,
                StoryArticle.article_time
                >= article.article_time - window,
                StoryArticle.article_time
                <= article.article_time + window,
                or_(*overlap_conditions),
            )
            .subquery()
        )

        memberships = list(
            db.scalars(
                select(StoryArticle)
                .join(
                    ranked_candidates,
                    ranked_candidates.c.membership_id
                    == StoryArticle.id,
                )
                .order_by(
                    ranked_candidates.c.story_rank,
                    ranked_candidates.c.article_time.desc(),
                    StoryArticle.id,
                )
                .limit(limit)
            ).all()
        )
        return tuple(
            StoryCandidate(
                story_id=membership.story_id,
                membership_id=membership.id,
                article_id=membership.article_id,
                article_time=membership.article_time,
                title_terms=tuple(
                    membership.title_terms
                ),
                entity_ids=tuple(
                    membership.entity_ids
                ),
                topic_ids=tuple(
                    membership.topic_ids
                ),
            )
            for membership in memberships
        )

    def has_other_active_memberships(
        self,
        db: Session,
        *,
        story_id: UUID,
        article_id: UUID,
    ) -> bool:
        return bool(
            db.scalar(
                select(
                    exists().where(
                        StoryArticle.story_id
                        == story_id,
                        StoryArticle.article_id
                        != article_id,
                        StoryArticle.deleted_at.is_(
                            None
                        ),
                    )
                )
            )
        )

    def create_story(
        self,
        db: Session,
        *,
        language_code: str | None,
    ) -> Story:
        story = Story(
            language_code=language_code,
        )

        db.add(story)
        db.flush()

        return story

    def replace_membership(
        self,
        db: Session,
        *,
        story_id: UUID,
        article_id: UUID,
        processing_run_id: UUID,
        article_title: str | None,
        article_time: datetime,
        title_terms: tuple[str, ...],
        entity_ids: tuple[UUID, ...],
        topic_ids: tuple[UUID, ...],
        similarity_score: float,
        match_kind: str,
        match_details: dict[str, object] | None,
        clustered_at: datetime,
    ) -> StoryArticle:
        story = self.get_story(
            db,
            story_id,
            for_update=True,
        )

        if story is None:
            raise ValueError(
                "target story is not active"
            )

        db.execute(
            update(StoryArticle)
            .where(
                StoryArticle.article_id
                == article_id,
                StoryArticle.deleted_at.is_(None),
            )
            .values(
                deleted_at=clustered_at,
                updated_at=clustered_at,
            )
        )

        db.flush()

        membership = StoryArticle(
            story_id=story_id,
            article_id=article_id,
            processing_run_id=processing_run_id,
            article_title=article_title,
            article_time=article_time,
            title_terms=list(title_terms),
            entity_ids=list(entity_ids),
            topic_ids=list(topic_ids),
            similarity_score=similarity_score,
            match_kind=match_kind,
            match_details=match_details,
            clustered_at=clustered_at,
        )

        db.add(membership)
        db.flush()

        return membership

    def deactivate_story_if_orphan(
        self,
        db: Session,
        *,
        story_id: UUID,
        now: datetime,
    ) -> bool:
        active_membership = exists(
            select(StoryArticle.id).where(
                StoryArticle.story_id
                == story_id,
                StoryArticle.deleted_at.is_(
                    None
                ),
            )
        )

        result = db.execute(
            update(Story)
            .where(
                Story.id == story_id,
                Story.deleted_at.is_(None),
                ~active_membership,
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )

        return (result.rowcount or 0) == 1

    def deactivate_ineligible_memberships(
        self,
        db: Session,
        *,
        now: datetime,
    ) -> list[UUID]:
        eligible_article = (
            select(Article.id)
            .join(
                Feed,
                Feed.id == Article.feed_id,
            )
            .join(
                Source,
                Source.id == Feed.source_id,
            )
            .where(
                Article.id
                == StoryArticle.article_id,
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Article.normalized_text.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
            .exists()
        )

        article_ids = list(
            db.scalars(
                update(StoryArticle)
                .where(
                    StoryArticle.deleted_at.is_(None),
                    ~eligible_article,
                )
                .values(
                    deleted_at=now,
                    updated_at=now,
                )
                .returning(
                    StoryArticle.article_id
                )
            ).all()
        )

        return article_ids

    def deactivate_orphan_stories(
        self,
        db: Session,
        *,
        now: datetime,
    ) -> int:
        active_membership = exists(
            select(StoryArticle.id).where(
                StoryArticle.story_id
                == Story.id,
                StoryArticle.deleted_at.is_(None),
            )
        )

        result = db.execute(
            update(Story)
            .where(
                Story.deleted_at.is_(None),
                ~active_membership,
            )
            .values(
                deleted_at=now,
                updated_at=now,
            )
        )

        return result.rowcount or 0
