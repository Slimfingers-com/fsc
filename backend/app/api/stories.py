from datetime import datetime
from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from app.analysis.provider import EntityType
from app.core.settings import settings
from app.db.session import get_db
from app.schemas.story import (
    StoryArticleRead,
    StoryDetailRead,
    StoryEntityRead,
    StoryPageRead,
    StorySourceRead,
    StorySummaryRead,
    StoryTopicRead,
)
from app.stories.postgresql import (
    PostgreSQLStoryReadProvider,
)
from app.stories.provider import (
    StoryFilters,
    StorySort,
)

router = APIRouter(
    prefix="/stories",
    tags=["stories"],
)


@router.get(
    "",
    response_model=StoryPageRead,
)
def list_stories(
    language: Annotated[
        str | None,
        Query(min_length=2, max_length=16),
    ] = None,
    source_id: UUID | None = None,
    source: Annotated[
        str | None,
        Query(min_length=1, max_length=255),
    ] = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    entity_id: UUID | None = None,
    entity_type: EntityType | None = None,
    topic_id: UUID | None = None,
    topic_slug: Annotated[
        str | None,
        Query(min_length=1, max_length=500),
    ] = None,
    min_articles: Annotated[
        int,
        Query(ge=1),
    ] = 1,
    min_sources: Annotated[
        int,
        Query(ge=1),
    ] = 1,
    sort: StorySort = StorySort.NEWEST,
    page: Annotated[
        int,
        Query(ge=1),
    ] = 1,
    page_size: Annotated[
        int | None,
        Query(ge=1),
    ] = None,
    db: Session = Depends(get_db),
):
    if (
        published_from is not None
        and published_to is not None
        and published_from > published_to
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "published_from must not be later "
                "than published_to."
            ),
        )

    size = (
        page_size
        or settings.story_default_page_size
    )
    size = min(
        size,
        settings.story_max_page_size,
    )

    result = PostgreSQLStoryReadProvider(
        db
    ).list_stories(
        filters=StoryFilters(
            language_code=language,
            source_id=source_id,
            source_slug=source,
            published_from=published_from,
            published_to=published_to,
            entity_id=entity_id,
            entity_type=entity_type,
            topic_id=topic_id,
            topic_slug=topic_slug,
            min_articles=min_articles,
            min_sources=min_sources,
        ),
        sort=sort,
        page=page,
        page_size=size,
    )

    return StoryPageRead(
        items=[
            StorySummaryRead.model_validate(item)
            for item in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=(
            ceil(
                result.total
                / result.page_size
            )
            if result.total
            else 0
        ),
    )


@router.get(
    "/{story_id}",
    response_model=StoryDetailRead,
)
def get_story(
    story_id: UUID,
    db: Session = Depends(get_db),
):
    result = PostgreSQLStoryReadProvider(
        db
    ).get_story(story_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Story not found.",
        )

    return StoryDetailRead(
        **StorySummaryRead.model_validate(
            result.summary
        ).model_dump(),
        sources=[
            StorySourceRead.model_validate(
                item
            )
            for item in result.sources
        ],
        articles=[
            StoryArticleRead.model_validate(
                item
            )
            for item in result.articles
        ],
        entities=[
            StoryEntityRead.model_validate(
                item
            )
            for item in result.entities
        ],
        topics=[
            StoryTopicRead.model_validate(
                item
            )
            for item in result.topics
        ],
    )
