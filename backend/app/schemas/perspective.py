from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.analysis.provider import TextPart
from app.perspectives.provider import PerspectiveKind


class PerspectiveRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    article_id: UUID
    claim_id: UUID
    holder_entity_id: UUID | None
    holder_text: str | None
    holder_start_offset: int | None = Field(
        default=None,
        ge=0,
    )
    holder_end_offset: int | None = Field(
        default=None,
        ge=1,
    )
    perspective_kind: PerspectiveKind
    evidence_text: str
    text_source: TextPart
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=1)
    sentence_index: int = Field(ge=0)
    confidence: float = Field(
        ge=0,
        le=1,
    )
    analysis_provider: str
    analysis_version: str
    analyzed_at: datetime


class PerspectiveContextRead(
    PerspectiveRead
):
    claim_text: str
    article_title: str | None
    article_url: str | None
    published_at: datetime | None
    source_id: UUID
    source_name: str
    source_slug: str
    story_id: UUID | None = None


class PerspectivePageRead(BaseModel):
    items: list[PerspectiveContextRead]
    total: int
    page: int
    page_size: int
    pages: int
