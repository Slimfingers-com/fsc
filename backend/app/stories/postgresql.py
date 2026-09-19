from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.entity import ArticleEntity, Entity
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.models.topic import ArticleTopic, Topic
from app.stories.provider import (
    StoryArticleItem,
    StoryDetail,
    StoryEntity,
    StoryFilters,
    StoryPage,
    StorySort,
    StorySource,
    StorySummary,
    StoryTopic,
)


class PostgreSQLStoryReadProvider:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _eligible_memberships():
        return (
            select(
                StoryArticle.id.label("membership_id"),
                StoryArticle.story_id.label("story_id"),
                StoryArticle.article_id.label("article_id"),
                StoryArticle.article_title.label("article_title"),
                StoryArticle.article_time.label("article_time"),
                StoryArticle.similarity_score.label("similarity_score"),
                StoryArticle.match_kind.label("match_kind"),
                StoryArticle.match_details.label("match_details"),
                StoryArticle.clustered_at.label("clustered_at"),
                Story.language_code.label("language_code"),
                Article.link.label("url"),
                Source.id.label("source_id"),
                Source.name.label("source_name"),
                Source.slug.label("source_slug"),
            )
            .join(
                Story,
                Story.id == StoryArticle.story_id,
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
                StoryArticle.deleted_at.is_(None),
                Story.deleted_at.is_(None),
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Article.normalized_text.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
            .cte("eligible_story_memberships")
        )

    @staticmethod
    def _summary_cte(eligible):
        return (
            select(
                eligible.c.story_id,
                eligible.c.language_code,
                func.count().label("article_count"),
                func.count(
                    func.distinct(eligible.c.source_id)
                ).label("source_count"),
                func.min(
                    eligible.c.article_time
                ).label("first_article_at"),
                func.max(
                    eligible.c.article_time
                ).label("last_article_at"),
            )
            .group_by(
                eligible.c.story_id,
                eligible.c.language_code,
            )
            .cte("story_summary")
        )

    @staticmethod
    def _representative_title_cte(eligible):
        return (
            select(
                eligible.c.story_id,
                eligible.c.article_title.label("title"),
            )
            .distinct(eligible.c.story_id)
            .order_by(
                eligible.c.story_id,
                eligible.c.article_time.desc(),
                eligible.c.membership_id.desc(),
            )
            .cte("story_representative_title")
        )

    @staticmethod
    def _matching_story_ids(
        eligible,
        filters: StoryFilters,
    ):
        statement = select(
            eligible.c.story_id
        ).select_from(eligible)

        if (
            filters.entity_id is not None
            or filters.entity_type is not None
        ):
            statement = (
                statement
                .join(
                    ArticleEntity,
                    ArticleEntity.article_id
                    == eligible.c.article_id,
                )
                .join(
                    Entity,
                    Entity.id
                    == ArticleEntity.entity_id,
                )
                .where(
                    ArticleEntity.deleted_at.is_(None),
                    Entity.deleted_at.is_(None),
                )
            )

            if filters.entity_id is not None:
                statement = statement.where(
                    ArticleEntity.entity_id
                    == filters.entity_id
                )

            if filters.entity_type is not None:
                statement = statement.where(
                    ArticleEntity.entity_type
                    == filters.entity_type
                )

        if (
            filters.topic_id is not None
            or filters.topic_slug is not None
        ):
            statement = (
                statement
                .join(
                    ArticleTopic,
                    ArticleTopic.article_id
                    == eligible.c.article_id,
                )
                .join(
                    Topic,
                    Topic.id == ArticleTopic.topic_id,
                )
                .where(
                    ArticleTopic.deleted_at.is_(None),
                    Topic.deleted_at.is_(None),
                )
            )

            if filters.topic_id is not None:
                statement = statement.where(
                    ArticleTopic.topic_id
                    == filters.topic_id
                )

            if filters.topic_slug is not None:
                statement = statement.where(
                    Topic.slug == filters.topic_slug
                )

        if filters.source_id is not None:
            statement = statement.where(
                eligible.c.source_id
                == filters.source_id
            )

        if filters.source_slug is not None:
            statement = statement.where(
                eligible.c.source_slug
                == filters.source_slug
            )

        if filters.published_from is not None:
            statement = statement.where(
                eligible.c.article_time
                >= filters.published_from
            )

        if filters.published_to is not None:
            statement = statement.where(
                eligible.c.article_time
                <= filters.published_to
            )

        return statement.distinct()

    def list_stories(
        self,
        *,
        filters: StoryFilters,
        sort: StorySort,
        page: int,
        page_size: int,
    ) -> StoryPage:
        eligible = self._eligible_memberships()
        summary = self._summary_cte(eligible)
        representative = (
            self._representative_title_cte(
                eligible
            )
        )

        statement = (
            select(
                summary.c.story_id,
                representative.c.title,
                summary.c.language_code,
                summary.c.article_count,
                summary.c.source_count,
                summary.c.first_article_at,
                summary.c.last_article_at,
            )
            .join(
                representative,
                representative.c.story_id
                == summary.c.story_id,
            )
            .where(
                summary.c.article_count
                >= filters.min_articles,
                summary.c.source_count
                >= filters.min_sources,
            )
        )

        if filters.language_code is not None:
            statement = statement.where(
                summary.c.language_code
                == filters.language_code
            )

        membership_filters_present = any(
            value is not None
            for value in (
                filters.source_id,
                filters.source_slug,
                filters.published_from,
                filters.published_to,
                filters.entity_id,
                filters.entity_type,
                filters.topic_id,
                filters.topic_slug,
            )
        )

        if membership_filters_present:
            statement = statement.where(
                summary.c.story_id.in_(
                    self._matching_story_ids(
                        eligible,
                        filters,
                    )
                )
            )

        total = (
            self.db.scalar(
                select(func.count())
                .select_from(
                    statement.subquery()
                )
            )
            or 0
        )

        if sort == StorySort.OLDEST:
            statement = statement.order_by(
                summary.c.first_article_at.asc(),
                summary.c.story_id.asc(),
            )
        elif sort == StorySort.LARGEST:
            statement = statement.order_by(
                summary.c.article_count.desc(),
                summary.c.source_count.desc(),
                summary.c.last_article_at.desc(),
                summary.c.story_id.asc(),
            )
        else:
            statement = statement.order_by(
                summary.c.last_article_at.desc(),
                summary.c.story_id.asc(),
            )

        rows = self.db.execute(
            statement
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return StoryPage(
            items=[
                StorySummary(
                    story_id=row.story_id,
                    title=row.title,
                    language_code=row.language_code,
                    article_count=int(
                        row.article_count
                    ),
                    source_count=int(
                        row.source_count
                    ),
                    first_article_at=(
                        row.first_article_at
                    ),
                    last_article_at=(
                        row.last_article_at
                    ),
                )
                for row in rows
            ],
            total=int(total),
            page=page,
            page_size=page_size,
        )

    def get_story(
        self,
        story_id: UUID,
    ) -> StoryDetail | None:
        eligible = self._eligible_memberships()
        summary = self._summary_cte(eligible)
        representative = (
            self._representative_title_cte(
                eligible
            )
        )

        row = self.db.execute(
            select(
                summary.c.story_id,
                representative.c.title,
                summary.c.language_code,
                summary.c.article_count,
                summary.c.source_count,
                summary.c.first_article_at,
                summary.c.last_article_at,
            )
            .join(
                representative,
                representative.c.story_id
                == summary.c.story_id,
            )
            .where(
                summary.c.story_id == story_id
            )
        ).one_or_none()

        if row is None:
            return None

        story_summary = StorySummary(
            story_id=row.story_id,
            title=row.title,
            language_code=row.language_code,
            article_count=int(row.article_count),
            source_count=int(row.source_count),
            first_article_at=row.first_article_at,
            last_article_at=row.last_article_at,
        )

        article_rows = self.db.execute(
            select(
                eligible.c.membership_id,
                eligible.c.article_id,
                eligible.c.article_title,
                eligible.c.url,
                eligible.c.article_time,
                eligible.c.source_id,
                eligible.c.source_name,
                eligible.c.source_slug,
                eligible.c.match_kind,
                eligible.c.similarity_score,
                eligible.c.match_details,
                eligible.c.clustered_at,
            )
            .where(
                eligible.c.story_id == story_id
            )
            .order_by(
                eligible.c.article_time.desc(),
                eligible.c.membership_id.asc(),
            )
        ).all()

        source_rows = self.db.execute(
            select(
                eligible.c.source_id,
                eligible.c.source_name,
                eligible.c.source_slug,
                func.count().label(
                    "article_count"
                ),
            )
            .where(
                eligible.c.story_id == story_id
            )
            .group_by(
                eligible.c.source_id,
                eligible.c.source_name,
                eligible.c.source_slug,
            )
            .order_by(
                func.count().desc(),
                eligible.c.source_name.asc(),
                eligible.c.source_id.asc(),
            )
        ).all()

        entity_rows = self.db.execute(
            select(
                Entity.id.label("entity_id"),
                Entity.canonical_name,
                Entity.entity_type,
                func.count(
                    func.distinct(
                        eligible.c.article_id
                    )
                ).label("article_count"),
            )
            .select_from(eligible)
            .join(
                ArticleEntity,
                ArticleEntity.article_id
                == eligible.c.article_id,
            )
            .join(
                Entity,
                Entity.id
                == ArticleEntity.entity_id,
            )
            .where(
                eligible.c.story_id == story_id,
                ArticleEntity.deleted_at.is_(None),
                Entity.deleted_at.is_(None),
            )
            .group_by(
                Entity.id,
                Entity.canonical_name,
                Entity.entity_type,
            )
            .order_by(
                func.count(
                    func.distinct(
                        eligible.c.article_id
                    )
                ).desc(),
                Entity.canonical_name.asc(),
                Entity.id.asc(),
            )
        ).all()

        topic_rows = self.db.execute(
            select(
                Topic.id.label("topic_id"),
                Topic.name,
                Topic.slug,
                func.count(
                    func.distinct(
                        eligible.c.article_id
                    )
                ).label("article_count"),
            )
            .select_from(eligible)
            .join(
                ArticleTopic,
                ArticleTopic.article_id
                == eligible.c.article_id,
            )
            .join(
                Topic,
                Topic.id
                == ArticleTopic.topic_id,
            )
            .where(
                eligible.c.story_id == story_id,
                ArticleTopic.deleted_at.is_(None),
                Topic.deleted_at.is_(None),
            )
            .group_by(
                Topic.id,
                Topic.name,
                Topic.slug,
            )
            .order_by(
                func.count(
                    func.distinct(
                        eligible.c.article_id
                    )
                ).desc(),
                Topic.name.asc(),
                Topic.id.asc(),
            )
        ).all()

        return StoryDetail(
            summary=story_summary,
            sources=[
                StorySource(
                    source_id=value.source_id,
                    name=value.source_name,
                    slug=value.source_slug,
                    article_count=int(
                        value.article_count
                    ),
                )
                for value in source_rows
            ],
            articles=[
                StoryArticleItem(
                    membership_id=(
                        value.membership_id
                    ),
                    article_id=value.article_id,
                    title=value.article_title,
                    url=value.url,
                    article_time=value.article_time,
                    source_id=value.source_id,
                    source_name=(
                        value.source_name
                    ),
                    source_slug=(
                        value.source_slug
                    ),
                    match_kind=value.match_kind,
                    similarity_score=float(
                        value.similarity_score
                    ),
                    match_details=(
                        value.match_details
                    ),
                    clustered_at=(
                        value.clustered_at
                    ),
                )
                for value in article_rows
            ],
            entities=[
                StoryEntity(
                    entity_id=value.entity_id,
                    canonical_name=(
                        value.canonical_name
                    ),
                    entity_type=value.entity_type,
                    article_count=int(
                        value.article_count
                    ),
                )
                for value in entity_rows
            ],
            topics=[
                StoryTopic(
                    topic_id=value.topic_id,
                    name=value.name,
                    slug=value.slug,
                    article_count=int(
                        value.article_count
                    ),
                )
                for value in topic_rows
            ],
        )
