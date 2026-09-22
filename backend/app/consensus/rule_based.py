from app.consensus.provider import (
    ConsensusAnalyzer,
    ConsensusKind,
    ConsensusSummaryResult,
    DifferenceKind,
    DifferenceSummaryResult,
    StoryConsensusInput,
    StoryConsensusResult,
)


class RuleBasedConsensusAnalyzer(ConsensusAnalyzer):
    provider = "local-rules"
    version = "1.0.0"

    def __init__(
        self,
        *,
        minimum_independent_sources: int = 2,
    ) -> None:
        if minimum_independent_sources < 2:
            raise ValueError(
                "minimum_independent_sources must be at least two"
            )
        self.minimum_independent_sources = (
            minimum_independent_sources
        )

    def configuration(self) -> dict[str, object]:
        return {
            "minimum_independent_sources": (
                self.minimum_independent_sources
            )
        }

    def analyze(
        self,
        story: StoryConsensusInput,
    ) -> StoryConsensusResult:
        consensus = tuple(
            ConsensusSummaryResult(
                group_id=group.group_id,
                consensus_kind=(
                    ConsensusKind.SHARED
                    if group.independent_source_count
                    >= self.minimum_independent_sources
                    else ConsensusKind.SINGLE_SOURCE
                ),
            )
            for group in sorted(
                story.groups,
                key=lambda value: str(value.group_id),
            )
        )
        differences = tuple(
            DifferenceSummaryResult(
                relation_id=item.relation_id,
                difference_kind=DifferenceKind.CONTRADICTION,
            )
            for item in sorted(
                story.differences,
                key=lambda value: str(value.relation_id),
            )
        )
        return StoryConsensusResult(
            consensus=consensus,
            differences=differences,
        )
