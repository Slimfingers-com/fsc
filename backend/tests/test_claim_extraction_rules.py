from uuid import uuid4

from app.analysis.provider import TextPart
from app.claims.provider import (
    ClaimExtractionInput,
)
from app.claims.rule_based import (
    RuleBasedClaimExtractor,
)


def test_rule_based_extractor_returns_exact_spans_and_skips_questions():
    body = (
        "Berlin beschließt heute ein neues Klimapaket. "
        "Wie geht es jetzt weiter? "
        "Die Kosten betragen 10 Milliarden Euro."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title=(
                "Regierung beschließt heute ein neues Klimapaket"
            ),
            normalized_text=body,
            language_code="de",
            published_at=None,
        )
    )

    assert [
        claim.claim_text
        for claim in result.claims
    ] == [
        "Regierung beschließt heute ein neues Klimapaket",
        "Berlin beschließt heute ein neues Klimapaket.",
        "Die Kosten betragen 10 Milliarden Euro.",
    ]

    for claim in result.claims:
        source = (
            "Regierung beschließt heute ein neues Klimapaket"
            if claim.text_source
            == TextPart.TITLE
            else body
        )

        assert source[
            claim.start_offset:
            claim.end_offset
        ] == claim.claim_text
        assert 0 <= claim.confidence <= 1


def test_rule_based_extractor_deduplicates_identical_claim_text():
    title = (
        "The government approved the new climate package"
    )
    body = title + "."

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title=title,
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    assert len(
        result.claims
    ) == 1
    assert (
        result.claims[0].text_source
        == TextPart.TITLE
    )
