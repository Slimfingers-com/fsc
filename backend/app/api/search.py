from datetime import datetime
from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import get_db
from app.schemas.search import SearchPageRead
from app.search.postgresql import PostgreSQLFullTextSearchProvider
from app.search.provider import SearchFilters, SearchSort

router = APIRouter(prefix="/search", tags=["search"])
@router.get("", response_model=SearchPageRead)
def search(
    q: Annotated[str | None, Query(max_length=500)] = None,
    language: Annotated[str | None, Query(min_length=2, max_length=16)] = None,
    source_id: UUID | None = None,
    source: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    entity_id: UUID | None = None,
    entity_type: str | None = None,
    topic_id: UUID | None = None,
    topic: str | None = None,
    sort: SearchSort = SearchSort.RELEVANCE,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    db: Session = Depends(get_db),
):
    size = page_size or settings.search_default_page_size
    size = min(size, settings.search_max_page_size)
    result = PostgreSQLFullTextSearchProvider(db).search(
        query=q,
        filters=SearchFilters(
            language_code=language,
            source_id=source_id,
            source_slug=source,
            published_from=published_from,
            published_to=published_to,
            entity_id=entity_id,
            entity_type=entity_type,
            topic_id=topic_id,
            topic_slug=topic,
        ),
        sort=sort,
        page=page,
        page_size=size,
    )
    return SearchPageRead(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=ceil(result.total / result.page_size) if result.total else 0,
    )
