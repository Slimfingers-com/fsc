from app.coverage.provider import (
    CoverageAnalyzer,
    CoverageGapKind,
    CoverageGapResult,
    MissingPerspectiveKind,
    MissingPerspectiveResult,
    StoryCoverageInput,
    StoryCoverageResult,
)
from app.enums.confirmation_role import counts_as_independent_confirmation


class RuleBasedCoverageAnalyzer(CoverageAnalyzer):
    provider = "local-rules"
    version = "1.0.0"

    def __init__(
        self,
        *,
        minimum_independent_content_sources: int = 2,
    ) -> None:
        if minimum_independent_content_sources < 2:
            raise ValueError(
                "minimum_independent_content_sources "
                "must be at least two"
            )
        self.minimum_independent_content_sources = (
            minimum_independent_content_sources
        )

    def configuration(self) -> dict[str, object]:
        return {
            "minimum_independent_content_sources": (
                self.minimum_independent_content_sources
            )
        }

    def analyze(
        self,
        story: StoryCoverageInput,
    ) -> StoryCoverageResult:
        content_sources = tuple(
            source
            for source in story.sources
            if not source.is_signal
        )
        signal_sources = tuple(
            source
            for source in story.sources
            if source.is_signal
        )
        independent_content_sources = {
            source.independence_key
            for source in content_sources
            if counts_as_independent_confirmation(
                source.confirmation_role
            )
        }

        gaps = []
        if (
            len(independent_content_sources)
            < self.minimum_independent_content_sources
        ):
            gaps.append(
                CoverageGapResult(
                    key="limited-independent-content-sources",
                    gap_kind=(
                        CoverageGapKind
                        .LIMITED_INDEPENDENT_CONTENT_SOURCES
                    ),
                    observed_count=len(
                        independent_content_sources
                    ),
                    minimum_expected=(
                        self
                        .minimum_independent_content_sources
                    ),
                )
            )

        if signal_sources and not content_sources:
            gaps.append(
                CoverageGapResult(
                    key="signal-without-content-coverage",
                    gap_kind=(
                        CoverageGapKind
                        .SIGNAL_WITHOUT_CONTENT_COVERAGE
                    ),
                    observed_count=len(
                        {
                            source.source_id
                            for source in signal_sources
                        }
                    ),
                    minimum_expected=None,
                )
            )

        missing = tuple(
            MissingPerspectiveResult(
                group_id=group.group_id,
                missing_kind=(
                    MissingPerspectiveKind
                    .NO_ATTRIBUTED_PERSPECTIVE
                ),
            )
            for group in sorted(
                story.groups,
                key=lambda item: str(item.group_id),
            )
            if group.attributed_perspective_count == 0
        )

        return StoryCoverageResult(
            gaps=tuple(gaps),
            missing_perspectives=missing,
        )
