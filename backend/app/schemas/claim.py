from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.analysis.provider import TextPart


class ClaimRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    article_id: UUID
    claim_text: str
    text_source: TextPart
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=1)
    sentence_index: int = Field(ge=0)
    confidence: float = Field(
        ge=0,
        le=1,
    )
    extraction_provider: str
    extraction_version: str
    extracted_at: datetime


class ClaimContextRead(ClaimRead):
    article_title: str | None
    article_url: str | None
    published_at: datetime | None
    source_id: UUID
    source_name: str
    source_slug: str
    story_id: UUID | None = None


class ClaimPageRead(BaseModel):
    items: list[ClaimContextRead]
    total: int
    page: int
    page_size: int
    pages: int
