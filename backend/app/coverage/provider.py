from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class CoverageGapKind(StrEnum):
    LIMITED_INDEPENDENT_CONTENT_SOURCES = (
        "limited_independent_content_sources"
    )
    SIGNAL_WITHOUT_CONTENT_COVERAGE = (
        "signal_without_content_coverage"
    )


class MissingPerspectiveKind(StrEnum):
    NO_ATTRIBUTED_PERSPECTIVE = (
        "no_attributed_perspective"
    )


@dataclass(frozen=True, slots=True)
class CoverageSourceInput:
    source_id: UUID
    independent_owner_key: str
    source_type: str
    coverage_scope: str | None
    country: str | None
    is_signal: bool


@dataclass(frozen=True, slots=True)
class CoverageGroupInput:
    group_id: UUID
    consensus_kind: str
    independent_source_count: int
    attributed_perspective_count: int


@dataclass(frozen=True, slots=True)
class CoverageDifferenceInput:
    relation_id: UUID
    left_group_id: UUID
    right_group_id: UUID


@dataclass(frozen=True, slots=True)
class StoryCoverageInput:
    story_id: UUID
    language_code: str | None
    sources: tuple[CoverageSourceInput, ...]
    groups: tuple[CoverageGroupInput, ...]
    differences: tuple[CoverageDifferenceInput, ...]


@dataclass(frozen=True, slots=True)
class CoverageGapResult:
    key: str
    gap_kind: CoverageGapKind
    observed_count: int
    minimum_expected: int | None


@dataclass(frozen=True, slots=True)
class MissingPerspectiveResult:
    group_id: UUID
    missing_kind: MissingPerspectiveKind


@dataclass(frozen=True, slots=True)
class StoryCoverageResult:
    gaps: tuple[CoverageGapResult, ...]
    missing_perspectives: tuple[MissingPerspectiveResult, ...]


class CoverageAnalyzer(ABC):
    provider: str
    version: str

    @abstractmethod
    def configuration(self) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def analyze(
        self,
        story: StoryCoverageInput,
    ) -> StoryCoverageResult:
        raise NotImplementedError
