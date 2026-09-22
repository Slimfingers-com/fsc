from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.consensus.provider import ConsensusKind, DifferenceKind


class ConsensusRead(BaseModel):
    id: UUID
    story_id: UUID
    claim_group_id: UUID
    representative_claim_id: UUID
    representative_claim_text: str
    consensus_kind: ConsensusKind
    claim_count: int = Field(ge=1)
    article_count: int = Field(ge=1)
    independent_source_count: int = Field(ge=1)
    evidence_item_count: int = Field(ge=0)
    evidence_source_count: int = Field(ge=0)
    attributed_perspective_count: int = Field(ge=0)
    analysis_provider: str
    analysis_version: str
    analyzed_at: datetime


class DifferenceRead(BaseModel):
    id: UUID
    story_id: UUID
    claim_relation_id: UUID
    left_group_id: UUID
    right_group_id: UUID
    left_claim_text: str
    right_claim_text: str
    difference_kind: DifferenceKind
    left_independent_source_count: int = Field(ge=1)
    right_independent_source_count: int = Field(ge=1)
    left_evidence_source_count: int = Field(ge=0)
    right_evidence_source_count: int = Field(ge=0)
    analysis_provider: str
    analysis_version: str
    analyzed_at: datetime


class ConsensusPageRead(BaseModel):
    items: list[ConsensusRead]
    total: int
    page: int
    page_size: int
    pages: int


class DifferencePageRead(BaseModel):
    items: list[DifferenceRead]
    total: int
    page: int
    page_size: int
    pages: int
