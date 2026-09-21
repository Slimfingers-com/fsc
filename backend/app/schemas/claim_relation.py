from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.claim_relations.provider import ClaimGroupMatchKind, ClaimRelationKind


class ClaimGroupSummaryRead(BaseModel):
    id: UUID
    story_id: UUID
    representative_claim_id: UUID
    representative_claim_text: str
    claim_count: int = Field(ge=1)
    article_count: int = Field(ge=1)
    source_count: int = Field(ge=1)
    confidence: float = Field(ge=0, le=1)
    analysis_provider: str
    analysis_version: str
    analyzed_at: datetime


class ClaimGroupMemberRead(BaseModel):
    id: UUID
    claim_id: UUID
    claim_text: str
    article_id: UUID
    article_title: str | None
    article_url: str | None
    published_at: datetime | None
    source_id: UUID
    source_name: str
    source_slug: str
    similarity_score: float = Field(ge=0, le=1)
    match_kind: ClaimGroupMatchKind


class ClaimGroupDetailRead(ClaimGroupSummaryRead):
    members: list[ClaimGroupMemberRead]


class ClaimGroupPageRead(BaseModel):
    items: list[ClaimGroupSummaryRead]
    total: int
    page: int
    page_size: int
    pages: int


class ClaimRelationRead(BaseModel):
    id: UUID
    story_id: UUID
    left_group_id: UUID
    right_group_id: UUID
    left_claim_text: str
    right_claim_text: str
    relation_kind: ClaimRelationKind
    confidence: float = Field(ge=0, le=1)
    analysis_provider: str
    analysis_version: str
    analyzed_at: datetime


class ClaimRelationPageRead(BaseModel):
    items: list[ClaimRelationRead]
    total: int
    page: int
    page_size: int
    pages: int
