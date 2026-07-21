from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SearchHitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    article_id: UUID
    title: str
    excerpt: str
    url: str | None
    source_id: UUID
    source_name: str
    source_slug: str
    language_code: str | None
    published_at: datetime | None
    relevance: float


class SearchPageRead(BaseModel):
    items: list[SearchHitRead]
    total: int
    page: int
    page_size: int
    pages: int
