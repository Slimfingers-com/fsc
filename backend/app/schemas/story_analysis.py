from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.claim_relations.provider import (
    ClaimGroupMatchKind,
)
from app.consensus.provider import (
    ConsensusKind,
    DifferenceKind,
)
from app.coverage.provider import (
    CoverageGapKind,
    MissingPerspectiveKind,
)
from app.evidence.provider import (
    EvidenceKind,
    EvidenceRelationKind,
)


class StoryAnalysisGenerationRead(BaseModel):
    claim_relations_run_id: UUID
    evidence_run_id: UUID
    consensus_run_id: UUID
    coverage_run_id: UUID


class StoryAnalysisMemberRead(BaseModel):
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


class StoryAnalysisEvidenceRead(BaseModel):
    id: UUID
    claim_id: UUID
    article_id: UUID
    source_id: UUID
    source_name: str
    source_slug: str
    evidence_kind: EvidenceKind
    relation_kind: EvidenceRelationKind
    evidence_text: str
    evidence_confidence: float = Field(
        ge=0,
        le=1,
    )
    relation_confidence: float = Field(
        ge=0,
        le=1,
    )


class StoryAnalysisConsensusRead(BaseModel):
    consensus_kind: ConsensusKind
    claim_count: int = Field(ge=1)
    article_count: int = Field(ge=1)
    independent_source_count: int = Field(
        ge=1
    )
    evidence_item_count: int = Field(ge=0)
    evidence_source_count: int = Field(ge=0)
    attributed_perspective_count: int = Field(
        ge=0
    )


class StoryAnalysisMissingPerspectiveRead(
    BaseModel
):
    missing_kind: MissingPerspectiveKind
    contradiction_relation_ids: list[UUID]


class StoryAnalysisClaimGroupRead(BaseModel):
    id: UUID
    representative_claim_id: UUID
    representative_claim_text: str
    confidence: float = Field(ge=0, le=1)
    members: list[StoryAnalysisMemberRead]
    evidence: list[StoryAnalysisEvidenceRead]
    consensus: StoryAnalysisConsensusRead
    missing_perspective: (
        StoryAnalysisMissingPerspectiveRead
        | None
    )


class StoryAnalysisDifferenceRead(BaseModel):
    id: UUID
    claim_relation_id: UUID
    left_group_id: UUID
    right_group_id: UUID
    left_claim_text: str
    right_claim_text: str
    difference_kind: DifferenceKind
    left_independent_source_count: int = Field(
        ge=1
    )
    right_independent_source_count: int = Field(
        ge=1
    )
    left_evidence_source_count: int = Field(
        ge=0
    )
    right_evidence_source_count: int = Field(
        ge=0
    )


class StoryAnalysisCoverageRead(BaseModel):
    article_count: int = Field(ge=1)
    source_count: int = Field(ge=1)
    content_source_count: int = Field(ge=0)
    signal_source_count: int = Field(ge=0)
    independent_content_owner_count: int = Field(
        ge=0
    )
    claim_group_count: int = Field(ge=1)
    shared_group_count: int = Field(ge=0)
    difference_count: int = Field(ge=0)
    attributed_group_count: int = Field(ge=0)
    source_type_counts: dict[str, int]
    coverage_scope_counts: dict[str, int]
    country_counts: dict[str, int]


class StoryAnalysisCoverageGapRead(BaseModel):
    id: UUID
    gap_kind: CoverageGapKind
    observed_count: int = Field(ge=0)
    minimum_expected: int | None = Field(
        default=None,
        ge=0,
    )


class StoryAnalysisRead(BaseModel):
    story_id: UUID
    language_code: str | None
    generations: StoryAnalysisGenerationRead
    claim_groups: list[
        StoryAnalysisClaimGroupRead
    ]
    differences: list[
        StoryAnalysisDifferenceRead
    ]
    coverage: StoryAnalysisCoverageRead
    coverage_gaps: list[
        StoryAnalysisCoverageGapRead
    ]
