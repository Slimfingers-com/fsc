from uuid import uuid4

from app.evidence.provider import (
    ClaimEvidenceInput,
    EvidenceKind,
    EvidenceRelationKind,
    StoryEvidenceAnalysisInput,
)
from app.evidence.rule_based import RuleBasedEvidenceAnalyzer


def make_claim(
    *,
    source_type: str,
    text: str = "The plan begins Monday.",
    title: str | None = None,
    quoted: bool = False,
):
    return ClaimEvidenceInput(
        claim_id=uuid4(),
        claim_group_id=uuid4(),
        article_id=uuid4(),
        source_id=uuid4(),
        source_type=source_type,
        claim_text=text,
        normalized_claim=text.casefold().rstrip("."),
        article_title=title,
        article_text=text,
        article_url="https://example.test/article",
        direct_quote_texts=(
            ("Direct quoted statement.", "Second direct quote.")
            if quoted
            else ()
        ),
    )


def analyze(item):
    return RuleBasedEvidenceAnalyzer().analyze(
        StoryEvidenceAnalysisInput(
            story_id=uuid4(),
            language_code="en",
            claims=(item,),
        )
    )


def test_primary_source_is_supporting_evidence():
    result = analyze(
        make_claim(
            source_type="PRIMARY_SOURCE"
        )
    )
    assert result.evidence[0].evidence_kind == EvidenceKind.PRIMARY_SOURCE
    assert result.links[0].relation_kind == EvidenceRelationKind.SUPPORTS


def test_numeric_primary_source_is_official_data():
    result = analyze(
        make_claim(
            source_type="PRIMARY_SOURCE",
            text="Inflation was 2.4 percent in August.",
        )
    )
    assert result.evidence[0].evidence_kind == EvidenceKind.OFFICIAL_DATA


def test_academic_source_is_study():
    result = analyze(
        make_claim(
            source_type="ACADEMIC"
        )
    )
    assert result.evidence[0].evidence_kind == EvidenceKind.STUDY


def test_direct_quote_takes_precedence():
    result = analyze(
        make_claim(
            source_type="NEWS",
            quoted=True,
        )
    )
    assert len(result.evidence) == 2
    assert {
        item.evidence_kind
        for item in result.evidence
    } == {EvidenceKind.DIRECT_QUOTE}
    assert {
        item.evidence_text
        for item in result.evidence
    } == {
        "Direct quoted statement.",
        "Second direct quote.",
    }


def test_press_release_is_detected():
    result = analyze(
        make_claim(
            source_type="COMPANY",
            title="Press release: quarterly update",
        )
    )
    assert result.evidence[0].evidence_kind == EvidenceKind.PRESS_RELEASE


def test_news_is_independent_reporting():
    result = analyze(
        make_claim(
            source_type="NEWS"
        )
    )
    assert (
        result.evidence[0].evidence_kind
        == EvidenceKind.INDEPENDENT_REPORTING
    )


def test_interest_group_is_context_by_default():
    result = analyze(
        make_claim(
            source_type="INTEREST_GROUP"
        )
    )
    assert result.evidence[0].evidence_kind == EvidenceKind.CONTEXT
    assert result.links[0].relation_kind == EvidenceRelationKind.CONTEXT


def test_unclassified_source_is_context_not_support():
    result = analyze(
        make_claim(
            source_type="SIGNAL"
        )
    )
    assert result.evidence[0].evidence_kind == EvidenceKind.CONTEXT
    assert result.links[0].relation_kind == EvidenceRelationKind.CONTEXT
