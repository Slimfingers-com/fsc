from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.evidence.provider import EvidenceKind, EvidenceRelationKind


class EvidenceRead(BaseModel):
    id: UUID
    story_id: UUID
    claim_group_id: UUID
    claim_id: UUID
    claim_text: str
    article_id: UUID
    article_title: str | None
    article_url: str | None
    published_at: datetime | None
    source_id: UUID
    source_name: str
    source_slug: str
    evidence_kind: EvidenceKind
    relation_kind: EvidenceRelationKind
    evidence_text: str
    evidence_confidence: float = Field(ge=0, le=1)
    relation_confidence: float = Field(ge=0, le=1)
    analysis_provider: str
    analysis_version: str
    analyzed_at: datetime


class EvidencePageRead(BaseModel):
    items: list[EvidenceRead]
    total: int
    page: int
    page_size: int
    pages: int
