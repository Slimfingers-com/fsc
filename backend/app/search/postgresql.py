import re

from sqlalchemy import Float, cast, func, literal, literal_column, select
from sqlalchemy.orm import Session

from app.models.search_document import SearchDocument
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.search.provider import SearchFilters, SearchHit, SearchPage, SearchProvider, SearchSort
from app.models.entity import ArticleEntity
from app.models.topic import ArticleTopic, Topic


class PostgreSQLFullTextSearchProvider(SearchProvider):
    def __init__(self, db: Session, *, text_config: str = "simple") -> None:
        if not re.fullmatch(r"[a-z_]+", text_config):
            raise ValueError("text_config must be a PostgreSQL text search configuration name")
        self.text_config = literal_column(f"'{text_config}'::regconfig")
        self.db = db

    def search(self, *, query: str | None, filters: SearchFilters, sort: SearchSort, page: int, page_size: int) -> SearchPage:
        normalized_query = (query or "").strip()
        tsquery = func.websearch_to_tsquery(self.text_config, normalized_query) if normalized_query else None
        relevance = (
            cast(func.ts_rank_cd(SearchDocument.search_vector, tsquery), Float)
            if tsquery is not None else literal(0.0, type_=Float)
        )
        conditions = [
            SearchDocument.deleted_at.is_(None),
            Article.deleted_at.is_(None),
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            Source.deleted_at.is_(None),
            Source.active.is_(True),
        ]
        if tsquery is not None:
            conditions.append(SearchDocument.search_vector.op("@@")(tsquery))
        if filters.language_code:
            conditions.append(SearchDocument.language_code == filters.language_code)
        if filters.source_id:
            conditions.append(SearchDocument.source_id == filters.source_id)
        if filters.source_slug:
            conditions.append(SearchDocument.source_slug == filters.source_slug)
        if filters.published_from:
            conditions.append(SearchDocument.published_at >= filters.published_from)
        if filters.published_to:
            conditions.append(SearchDocument.published_at <= filters.published_to)
        if filters.entity_id:
            conditions.append(select(ArticleEntity.id).where(ArticleEntity.article_id == Article.id, ArticleEntity.entity_id == filters.entity_id).exists())
        if filters.entity_type:
            conditions.append(select(ArticleEntity.id).where(ArticleEntity.article_id == Article.id, ArticleEntity.entity_type == filters.entity_type).exists())
        if filters.topic_id:
            conditions.append(select(ArticleTopic.id).where(ArticleTopic.article_id == Article.id, ArticleTopic.topic_id == filters.topic_id).exists())
        if filters.topic_slug:
            conditions.append(select(ArticleTopic.id).join(Topic).where(ArticleTopic.article_id == Article.id, Topic.slug == filters.topic_slug, Topic.deleted_at.is_(None)).exists())

        base = (
            select(SearchDocument)
            .join(Article, Article.id == SearchDocument.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(Source, Source.id == Feed.source_id)
        )
        total = self.db.scalar(
            select(func.count()).select_from(base.where(*conditions).subquery())
        ) or 0
        excerpt = (
            func.ts_headline(
                self.text_config,
                SearchDocument.body,
                tsquery,
                "StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15",
            )
            if tsquery is not None else func.left(SearchDocument.body, 300)
        )
        statement = (
            select(SearchDocument, relevance.label("relevance"), excerpt.label("excerpt"))
            .join(Article, Article.id == SearchDocument.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(Source, Source.id == Feed.source_id)
            .where(*conditions)
        )
        if sort == SearchSort.OLDEST:
            statement = statement.order_by(SearchDocument.published_at.asc().nullslast(), SearchDocument.id.asc())
        elif sort == SearchSort.NEWEST or not normalized_query:
            statement = statement.order_by(SearchDocument.published_at.desc().nullslast(), SearchDocument.id.asc())
        else:
            statement = statement.order_by(relevance.desc(), SearchDocument.published_at.desc().nullslast(), SearchDocument.id.asc())
        rows = self.db.execute(statement.offset((page - 1) * page_size).limit(page_size)).all()
        items = [
            SearchHit(
                document_id=document.id,
                article_id=document.article_id,
                title=document.title,
                excerpt=excerpt_text,
                url=document.url,
                source_id=document.source_id,
                source_name=document.source_name,
                source_slug=document.source_slug,
                language_code=document.language_code,
                published_at=document.published_at,
                relevance=float(rank),
            )
            for document, rank, excerpt_text in rows
        ]
        return SearchPage(items=items, total=total, page=page, page_size=page_size)
