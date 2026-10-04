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


def test_rule_based_extractor_keeps_decimal_and_clock_periods():
    body = (
        "The aircraft flew 2.5 miles before landing at 11.30pm. "
        "The airport remained open overnight."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Airport remains open after late landing",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    body_claims = [
        claim.claim_text
        for claim in result.claims
        if claim.text_source == TextPart.BODY
    ]
    assert body_claims == [
        "The aircraft flew 2.5 miles before landing at 11.30pm.",
        "The airport remained open overnight.",
    ]


def test_rule_based_extractor_keeps_german_ordinals_and_dates():
    body = (
        "In München geht das 191. Oktoberfest am Abend zu Ende. "
        "Zwei Jahre nach dem 7. Oktober beginnt die Gedenkveranstaltung."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="München beendet das Oktoberfest",
            normalized_text=body,
            language_code="de",
            published_at=None,
        )
    )

    body_claims = [
        claim.claim_text
        for claim in result.claims
        if claim.text_source == TextPart.BODY
    ]
    assert body_claims == [
        "In München geht das 191. Oktoberfest am Abend zu Ende.",
        "Zwei Jahre nach dem 7. Oktober beginnt die Gedenkveranstaltung.",
    ]


def test_rule_based_extractor_still_splits_real_sentence_after_number():
    body = (
        "Die Partei erhielt Listenplatz 3. "
        "Danach begann die Debatte im Parlament."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Partei diskutiert nach der Listenaufstellung",
            normalized_text=body,
            language_code="de",
            published_at=None,
        )
    )

    body_claims = [
        claim.claim_text
        for claim in result.claims
        if claim.text_source == TextPart.BODY
    ]
    assert body_claims == [
        "Die Partei erhielt Listenplatz 3.",
        "Danach begann die Debatte im Parlament.",
    ]


def test_rule_based_extractor_filters_publishing_meta_claims():
    body = (
        "The government announced a new housing programme. "
        "The post Government unveils housing programme appeared first on Example News."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Government announces new housing programme",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    assert all(
        "appeared first on" not in claim.claim_text.lower()
        for claim in result.claims
    )
    assert any(
        "announced a new housing programme" in claim.claim_text
        for claim in result.claims
    )


def test_rule_based_extractor_filters_incomplete_ellipsis_claims():
    body = (
        "Officials said negotiations would continue… "
        "The cabinet meets again on Tuesday."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Cabinet meets again on Tuesday",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    body_claims = [
        claim.claim_text
        for claim in result.claims
        if claim.text_source == TextPart.BODY
    ]
    assert body_claims == [
        "The cabinet meets again on Tuesday.",
    ]


def test_rule_based_extractor_filters_generic_newsblog_meta_claim():
    body = (
        "In unserem Newsblog halten wir Sie auf dem Laufenden. "
        "Die AfD wurde stärkste Kraft, gefolgt von der SPD."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="AfD wird stärkste Kraft",
            normalized_text=body,
            language_code="de",
            published_at=None,
        )
    )

    assert all(
        "Newsblog" not in claim.claim_text
        for claim in result.claims
    )
    assert any(
        "AfD wurde stärkste Kraft" in claim.claim_text
        for claim in result.claims
    )


def test_rule_based_extractor_keeps_dotted_initialism_together():
    body = (
        "A U.S. Marine was arrested in Okinawa on Sunday. "
        "Officials said the investigation is continuing."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="U.S. Marine arrested in Okinawa",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    body_claims = [
        claim.claim_text
        for claim in result.claims
        if claim.text_source == TextPart.BODY
    ]
    assert body_claims == [
        "A U.S. Marine was arrested in Okinawa on Sunday.",
        "Officials said the investigation is continuing.",
    ]


def test_rule_based_extractor_splits_sentence_boundary_without_space():
    body = (
        "Der SC Magdeburg hat die Heimspiel-Woche erfolgreich beendet."
        "Gegen Erlangen gelang ein klarer Erfolg."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Magdeburg gewinnt gegen Erlangen",
            normalized_text=body,
            language_code="de",
            published_at=None,
        )
    )

    body_claims = [
        claim.claim_text
        for claim in result.claims
        if claim.text_source == TextPart.BODY
    ]
    assert body_claims == [
        "Der SC Magdeburg hat die Heimspiel-Woche erfolgreich beendet.",
        "Gegen Erlangen gelang ein klarer Erfolg.",
    ]


def test_rule_based_extractor_filters_editorial_charter_meta():
    body = (
        "The opposition criticised the government's plan. "
        "Our Standards: The GB News Editorial Charter"
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Opposition criticises government plan",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    assert all(
        "Editorial Charter" not in claim.claim_text
        for claim in result.claims
    )


def test_rule_based_extractor_filters_embedded_social_url_fragment():
    body = (
        "The minister announced the proposal today. "
        "Watch the clip at pic.twitter.com/AbCdEf123"
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Minister announces proposal",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    assert all(
        "twitter.com" not in claim.claim_text
        for claim in result.claims
    )


def test_rule_based_extractor_keeps_hyphenated_initialism_together():
    body = (
        "The talks reinforced the Japan-U.S. military alliance. "
        "Officials welcomed the agreement."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Japan and U.S. reinforce military alliance",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    body_claims = [
        claim.claim_text
        for claim in result.claims
        if claim.text_source == TextPart.BODY
    ]
    assert body_claims == [
        "The talks reinforced the Japan-U.S. military alliance.",
        "Officials welcomed the agreement.",
    ]


def test_rule_based_extractor_keeps_legitimate_the_post_sentence():
    body = (
        "The post started with a Polaroid image of the actor at the lake. "
        "The next slide showed her water-skiing behind a boat."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Actor shares photos from lake holiday",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    body_claims = [
        claim.claim_text
        for claim in result.claims
        if claim.text_source == TextPart.BODY
    ]
    assert (
        "The post started with a Polaroid image of the actor at the lake."
        in body_claims
    )


def test_rule_based_extractor_filters_multisentence_publishing_footer():
    body = (
        "Police seized the shipment after a traffic stop. "
        "The post Police Allegedly Destroyed $37,000 of Legal Hemp. "
        "Georgia's Supreme Court Just Upended 60 Years of Precedent. "
        "appeared first on Reason Magazine."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Police seize hemp shipment",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    body_claims = [
        claim.claim_text
        for claim in result.claims
        if claim.text_source == TextPart.BODY
    ]
    assert body_claims == [
        "Police seized the shipment after a traffic stop.",
    ]


def test_rule_based_extractor_filters_first_appeared_on_footer_variant():
    body = (
        "The organisation announced its anniversary programme. "
        "The post Festwoche zum 40. Jubiläum first appeared on PRO ASYL."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Organisation announces anniversary programme",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    assert all(
        "first appeared on" not in claim.claim_text.lower()
        for claim in result.claims
    )
    assert all(
        "Festwoche zum 40." not in claim.claim_text
        for claim in result.claims
    )


def test_rule_based_extractor_keeps_the_post_also_came_prose():
    body = (
        "The opposition released an attack advert in the morning. "
        "The post also came just hours after the party published its manifesto."
    )

    result = RuleBasedClaimExtractor().extract(
        ClaimExtractionInput(
            article_id=uuid4(),
            title="Opposition releases attack advert",
            normalized_text=body,
            language_code="en",
            published_at=None,
        )
    )

    assert any(
        claim.claim_text.startswith("The post also came just hours")
        for claim in result.claims
    )
