from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import get_db
from app.models.article import Article
from app.models.claim import ArticleClaim
from app.models.feed import Feed
from app.models.perspective import ArticlePerspective
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.perspectives.provider import PerspectiveKind
from app.schemas.perspective import (
    PerspectiveContextRead,
    PerspectivePageRead,
    PerspectiveRead,
)


router = APIRouter(
    tags=["perspectives"],
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
) -> PerspectiveContextRead:
    perspective = row[0]

    return PerspectiveContextRead(
        **PerspectiveRead.model_validate(
            perspective
        ).model_dump(),
        claim_text=row.claim_text,
        article_title=(
            row.article_title
        ),
        article_url=row.article_url,
        published_at=row.published_at,
        source_id=row.source_id,
        source_name=row.source_name,
        source_slug=row.source_slug,
        story_id=row.story_id,
    )


@router.get(
    "/articles/{article_id}/perspectives",
    response_model=list[PerspectiveRead],
)
def article_perspectives(
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
            Article.id == article_id,
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

    items = list(
        db.scalars(
            select(
                ArticlePerspective
            )
            .join(
                ArticleClaim,
                ArticleClaim.id
                == ArticlePerspective.claim_id,
            )
            .join(
                Article,
                Article.id
                == ArticlePerspective.article_id,
            )
            .join(Feed)
            .join(Source)
            .where(
                ArticlePerspective.article_id
                == article_id,
                ArticlePerspective.deleted_at.is_(
                    None
                ),
                ArticleClaim.deleted_at.is_(
                    None
                ),
                ArticleClaim.article_id
                == ArticlePerspective.article_id,
                *_article_conditions(),
            )
            .order_by(
                ArticlePerspective.claim_id,
                ArticlePerspective.perspective_kind,
                ArticlePerspective.start_offset,
                ArticlePerspective.id,
            )
        ).all()
    )

    return [
        PerspectiveRead.model_validate(
            item
        )
        for item in items
    ]


@router.get(
    "/claims/{claim_id}/perspectives",
    response_model=list[PerspectiveRead],
)
def claim_perspectives(
    claim_id: UUID,
    db: Session = Depends(
        get_db
    ),
):
    claim_exists = db.scalar(
        select(ArticleClaim.id)
        .join(
            Article,
            Article.id
            == ArticleClaim.article_id,
        )
        .join(Feed)
        .join(Source)
        .where(
            ArticleClaim.id
            == claim_id,
            ArticleClaim.deleted_at.is_(
                None
            ),
            *_article_conditions(),
        )
    )

    if claim_exists is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    items = list(
        db.scalars(
            select(
                ArticlePerspective
            )
            .join(
                ArticleClaim,
                ArticleClaim.id
                == ArticlePerspective.claim_id,
            )
            .where(
                ArticlePerspective.claim_id
                == claim_id,
                ArticlePerspective.deleted_at.is_(
                    None
                ),
                ArticleClaim.deleted_at.is_(
                    None
                ),
                ArticleClaim.article_id
                == ArticlePerspective.article_id,
            )
            .order_by(
                ArticlePerspective.perspective_kind,
                ArticlePerspective.start_offset,
                ArticlePerspective.id,
            )
        ).all()
    )

    return [
        PerspectiveRead.model_validate(
            item
        )
        for item in items
    ]


@router.get(
    "/stories/{story_id}/perspectives",
    response_model=PerspectivePageRead,
)
def story_perspectives(
    story_id: UUID,
    perspective_kind: (
        PerspectiveKind | None
    ) = None,
    holder_entity_id: UUID | None = None,
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
        .join(Feed)
        .join(Source)
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
        or settings.perspective_default_page_size,
        settings.perspective_max_page_size,
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
        ArticlePerspective.deleted_at.is_(
            None
        ),
        ArticleClaim.deleted_at.is_(
            None
        ),
        ArticleClaim.article_id
        == ArticlePerspective.article_id,
        ArticlePerspective.confidence
        >= min_confidence,
        *_article_conditions(),
    ]

    if perspective_kind is not None:
        conditions.append(
            ArticlePerspective.perspective_kind
            == perspective_kind
        )

    if holder_entity_id is not None:
        conditions.append(
            ArticlePerspective.holder_entity_id
            == holder_entity_id
        )

    if source_id is not None:
        conditions.append(
            Source.id
            == source_id
        )

    from_clause = (
        ArticlePerspective.__table__
        .join(
            ArticleClaim.__table__,
            ArticleClaim.id
            == ArticlePerspective.claim_id,
        )
        .join(
            Article.__table__,
            Article.id
            == ArticlePerspective.article_id,
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
                    ArticlePerspective.id
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
            ArticlePerspective,
            ArticleClaim.claim_text.label(
                "claim_text"
            ),
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
            ArticlePerspective.claim_id,
            ArticlePerspective.perspective_kind,
            ArticlePerspective.start_offset,
            ArticlePerspective.id,
        )
        .offset(
            (page - 1)
            * size
        )
        .limit(size)
    ).all()

    return PerspectivePageRead(
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
