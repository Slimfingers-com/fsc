from uuid import uuid4

from app.analysis.provider import EntityType, TextPart
from app.perspectives.provider import (
    PerspectiveAnalysisInput,
    PerspectiveClaimInput,
    PerspectiveEntityMentionInput,
    PerspectiveKind,
)
from app.perspectives.rule_based import (
    RuleBasedPerspectiveAnalyzer,
)


def _input(
    text: str,
    *,
    with_holder: bool = True,
):
    claim_id = uuid4()
    mention_id = uuid4()
    entity_id = uuid4()
    claim = PerspectiveClaimInput(
        claim_id=claim_id,
        claim_text=text,
        claim_hash="a" * 64,
        text_source=TextPart.BODY,
        start_offset=0,
        end_offset=len(text),
        sentence_index=0,
        confidence=0.9,
    )
    mentions = ()

    if with_holder:
        holder = "Alice Smith"
        start = text.index(holder)
        mentions = (
            PerspectiveEntityMentionInput(
                mention_id=mention_id,
                entity_id=entity_id,
                mention_text=holder,
                entity_type=(
                    EntityType.PERSON
                ),
                text_source=(
                    TextPart.BODY
                ),
                start_offset=start,
                end_offset=(
                    start
                    + len(holder)
                ),
                sentence_index=0,
                confidence=0.9,
                salience=0.9,
            ),
        )

    return (
        PerspectiveAnalysisInput(
            article_id=uuid4(),
            title="",
            normalized_text=text,
            language_code="en",
            claims=(claim,),
            entity_mentions=mentions,
        ),
        claim_id,
        (
            mention_id
            if with_holder
            else None
        ),
    )


def test_rule_based_attributes_reported_statement():
    text = (
        "Alice Smith said the climate plan will begin Monday."
    )
    article, claim_id, mention_id = (
        _input(text)
    )

    result = (
        RuleBasedPerspectiveAnalyzer()
        .analyze(article)
    )

    assert len(
        result.attributions
    ) == 1
    item = result.attributions[0]
    assert item.claim_id == claim_id
    assert (
        item.perspective_kind
        == PerspectiveKind.REPORTED
    )
    assert (
        item.holder_mention_id
        == mention_id
    )
    assert item.evidence_text == text
    assert item.start_offset == 0
    assert item.end_offset == len(
        text
    )


def test_rule_based_marks_quoted_statement():
    text = (
        'Alice Smith said "the climate plan will begin Monday".'
    )
    article, _, mention_id = (
        _input(text)
    )

    item = (
        RuleBasedPerspectiveAnalyzer()
        .analyze(article)
        .attributions[0]
    )

    assert (
        item.perspective_kind
        == PerspectiveKind.QUOTED
    )
    assert (
        item.holder_mention_id
        == mention_id
    )


def test_rule_based_falls_back_to_unattributed():
    text = (
        "The climate plan will begin Monday."
    )
    article, claim_id, _ = (
        _input(
            text,
            with_holder=False,
        )
    )

    item = (
        RuleBasedPerspectiveAnalyzer()
        .analyze(article)
        .attributions[0]
    )

    assert item.claim_id == claim_id
    assert (
        item.perspective_kind
        == PerspectiveKind.UNATTRIBUTED
    )
    assert (
        item.holder_mention_id
        is None
    )

def test_rule_based_does_not_attribute_distant_reporting_verb_to_earlier_entity():
    text = (
        "Alice Smith attended while Bob Jones said "
        "the climate plan will begin Monday."
    )
    article, claim_id, _ = _input(
        text
    )
    bob_mention_id = uuid4()
    bob_entity_id = uuid4()
    bob_start = text.index(
        "Bob Jones"
    )

    article = PerspectiveAnalysisInput(
        article_id=article.article_id,
        title=article.title,
        normalized_text=(
            article.normalized_text
        ),
        language_code=(
            article.language_code
        ),
        claims=article.claims,
        entity_mentions=(
            article.entity_mentions[0],
            PerspectiveEntityMentionInput(
                mention_id=bob_mention_id,
                entity_id=bob_entity_id,
                mention_text="Bob Jones",
                entity_type=(
                    EntityType.PERSON
                ),
                text_source=(
                    TextPart.BODY
                ),
                start_offset=bob_start,
                end_offset=(
                    bob_start
                    + len("Bob Jones")
                ),
                sentence_index=0,
                confidence=0.9,
                salience=0.9,
            ),
        ),
    )

    item = (
        RuleBasedPerspectiveAnalyzer()
        .analyze(article)
        .attributions[0]
    )

    assert item.claim_id == claim_id
    assert (
        item.perspective_kind
        == PerspectiveKind.REPORTED
    )
    assert (
        item.holder_mention_id
        == bob_mention_id
    )
