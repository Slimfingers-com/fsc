from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import get_db
from app.models.article import Article
from app.models.claim import ArticleClaim
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import (
    Story,
    StoryArticle,
)
from app.schemas.claim import (
    ClaimContextRead,
    ClaimPageRead,
    ClaimRead,
)

router = APIRouter(
    tags=["claims"],
)


def _article_conditions():
    return (
        Article.deleted_at.is_(None),
        Article.normalized_at.is_not(
            None
        ),
        Article.normalized_text.is_not(
            None
        ),
        Feed.deleted_at.is_(None),
        Feed.active.is_(True),
        Source.deleted_at.is_(None),
        Source.active.is_(True),
    )


def _active_story_id():
    return (
        select(
            StoryArticle.story_id
        )
        .join(
            Story,
            Story.id
            == StoryArticle.story_id,
        )
        .where(
            StoryArticle.article_id
            == Article.id,
            StoryArticle.deleted_at.is_(
                None
            ),
            Story.deleted_at.is_(
                None
            ),
        )
        .limit(1)
        .scalar_subquery()
    )


def _context_from_row(
    row,
) -> ClaimContextRead:
    claim = row[0]

    return ClaimContextRead(
        **ClaimRead.model_validate(
            claim
        ).model_dump(),
        article_title=(
            row.article_title
        ),
        article_url=row.article_url,
        published_at=(
            row.published_at
        ),
        source_id=row.source_id,
        source_name=row.source_name,
        source_slug=row.source_slug,
        story_id=row.story_id,
    )


@router.get(
    "/articles/{article_id}/claims",
    response_model=list[ClaimRead],
)
def article_claims(
    article_id: UUID,
    db: Session = Depends(
        get_db
    ),
):
    article_exists = db.scalar(
        select(Article.id)
        .join(Feed)
        .join(Source)
        .where(
            Article.id
            == article_id,
            Article.deleted_at.is_(
                None
            ),
            Feed.deleted_at.is_(
                None
            ),
            Feed.active.is_(True),
            Source.deleted_at.is_(
                None
            ),
            Source.active.is_(True),
        )
    )

    if article_exists is None:
        raise HTTPException(
            status_code=404,
            detail="Article not found.",
        )

    claims = list(
        db.scalars(
            select(ArticleClaim)
            .join(Article)
            .join(Feed)
            .join(Source)
            .where(
                Article.id
                == article_id,
                *_article_conditions(),
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

    return [
        ClaimRead.model_validate(
            claim
        )
        for claim in claims
    ]


@router.get(
    "/claims/{claim_id}",
    response_model=ClaimContextRead,
)
def claim_detail(
    claim_id: UUID,
    db: Session = Depends(
        get_db
    ),
):
    statement = (
        select(
            ArticleClaim,
            Article.title.label(
                "article_title"
            ),
            Article.link.label(
                "article_url"
            ),
            Article.published_at.label(
                "published_at"
            ),
            Source.id.label(
                "source_id"
            ),
            Source.name.label(
                "source_name"
            ),
            Source.slug.label(
                "source_slug"
            ),
            _active_story_id().label(
                "story_id"
            ),
        )
        .join(
            Article,
            Article.id
            == ArticleClaim.article_id,
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
            ArticleClaim.id
            == claim_id,
            ArticleClaim.deleted_at.is_(
                None
            ),
            *_article_conditions(),
        )
    )

    row = db.execute(
        statement
    ).one_or_none()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    return _context_from_row(
        row
    )


@router.get(
    "/stories/{story_id}/claims",
    response_model=ClaimPageRead,
)
def story_claims(
    story_id: UUID,
    min_confidence: Annotated[
        float,
        Query(
            ge=0,
            le=1,
        ),
    ] = 0.0,
    source_id: UUID | None = None,
    page: Annotated[
        int,
        Query(ge=1),
    ] = 1,
    page_size: Annotated[
        int | None,
        Query(ge=1),
    ] = None,
    db: Session = Depends(
        get_db
    ),
):
    story_exists = db.scalar(
        select(Story.id)
        .join(
            StoryArticle,
            StoryArticle.story_id
            == Story.id,
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
            Story.id == story_id,
            Story.deleted_at.is_(
                None
            ),
            StoryArticle.deleted_at.is_(
                None
            ),
            *_article_conditions(),
        )
        .limit(1)
    )

    if story_exists is None:
        raise HTTPException(
            status_code=404,
            detail="Story not found.",
        )

    size = min(
        page_size
        or settings.claim_default_page_size,
        settings.claim_max_page_size,
    )

    conditions = [
        StoryArticle.story_id
        == story_id,
        StoryArticle.deleted_at.is_(
            None
        ),
        Story.deleted_at.is_(
            None
        ),
        ArticleClaim.deleted_at.is_(
            None
        ),
        ArticleClaim.confidence
        >= min_confidence,
        *_article_conditions(),
    ]

    if source_id is not None:
        conditions.append(
            Source.id
            == source_id
        )

    from_clause = (
        ArticleClaim.__table__
        .join(
            Article.__table__,
            Article.id
            == ArticleClaim.article_id,
        )
        .join(
            Feed.__table__,
            Feed.id
            == Article.feed_id,
        )
        .join(
            Source.__table__,
            Source.id
            == Feed.source_id,
        )
        .join(
            StoryArticle.__table__,
            StoryArticle.article_id
            == Article.id,
        )
        .join(
            Story.__table__,
            Story.id
            == StoryArticle.story_id,
        )
    )

    total = (
        db.scalar(
            select(
                func.count(
                    ArticleClaim.id
                )
            )
            .select_from(
                from_clause
            )
            .where(
                *conditions
            )
        )
        or 0
    )

    rows = db.execute(
        select(
            ArticleClaim,
            Article.title.label(
                "article_title"
            ),
            Article.link.label(
                "article_url"
            ),
            Article.published_at.label(
                "published_at"
            ),
            Source.id.label(
                "source_id"
            ),
            Source.name.label(
                "source_name"
            ),
            Source.slug.label(
                "source_slug"
            ),
            Story.id.label(
                "story_id"
            ),
        )
        .select_from(
            from_clause
        )
        .where(
            *conditions
        )
        .order_by(
            Article.published_at
            .desc()
            .nullslast(),
            Article.created_at.desc(),
            Article.id,
            ArticleClaim.text_source,
            ArticleClaim.sentence_index,
            ArticleClaim.start_offset,
            ArticleClaim.id,
        )
        .offset(
            (page - 1)
            * size
        )
        .limit(size)
    ).all()

    return ClaimPageRead(
        items=[
            _context_from_row(
                row
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=size,
        pages=(
            ceil(
                total
                / size
            )
            if total
            else 0
        ),
    )
