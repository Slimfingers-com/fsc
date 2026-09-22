from uuid import uuid4

from app.coverage.provider import (
    CoverageGapKind,
    CoverageGroupInput,
    CoverageSourceInput,
    MissingPerspectiveKind,
    StoryCoverageInput,
)
from app.coverage.rule_based import (
    RuleBasedCoverageAnalyzer,
)


def source(
    *,
    owner: str,
    signal: bool = False,
):
    return CoverageSourceInput(
        source_id=uuid4(),
        independent_owner_key=owner,
        source_type=(
            "SIGNAL"
            if signal
            else "NEWS"
        ),
        coverage_scope=None,
        country=None,
        is_signal=signal,
    )


def group(
    *,
    attributed: int,
):
    return CoverageGroupInput(
        group_id=uuid4(),
        consensus_kind="single_source",
        independent_source_count=1,
        attributed_perspective_count=attributed,
    )


def analyze(
    sources,
    groups=(),
):
    return (
        RuleBasedCoverageAnalyzer()
        .analyze(
            StoryCoverageInput(
                story_id=uuid4(),
                language_code="en",
                sources=tuple(sources),
                groups=tuple(groups),
                differences=(),
            )
        )
    )


def test_two_independent_content_sources_have_no_source_gap():
    result = analyze(
        [
            source(owner="a"),
            source(owner="b"),
        ]
    )
    assert result.gaps == ()


def test_one_content_owner_creates_limited_source_gap():
    result = analyze(
        [
            source(owner="same"),
            source(owner="same"),
        ]
    )
    assert len(result.gaps) == 1
    assert (
        result.gaps[0].gap_kind
        == CoverageGapKind
        .LIMITED_INDEPENDENT_CONTENT_SOURCES
    )
    assert result.gaps[0].observed_count == 1


def test_signal_only_creates_attention_and_content_gaps():
    result = analyze(
        [
            source(
                owner="signal-a",
                signal=True,
            )
        ]
    )
    assert {
        gap.gap_kind
        for gap in result.gaps
    } == {
        CoverageGapKind
        .LIMITED_INDEPENDENT_CONTENT_SOURCES,
        CoverageGapKind
        .SIGNAL_WITHOUT_CONTENT_COVERAGE,
    }


def test_only_observed_group_without_attribution_is_missing():
    missing_group = group(
        attributed=0
    )
    attributed_group = group(
        attributed=2
    )
    result = analyze(
        [
            source(owner="a"),
            source(owner="b"),
        ],
        [
            missing_group,
            attributed_group,
        ],
    )
    assert len(
        result.missing_perspectives
    ) == 1
    assert (
        result.missing_perspectives[0]
        .group_id
        == missing_group.group_id
    )
    assert (
        result.missing_perspectives[0]
        .missing_kind
        == MissingPerspectiveKind
        .NO_ATTRIBUTED_PERSPECTIVE
    )
