from app.core.agency_provenance import detect_agency_provenance
from app.enums.source_dependency import ArticleProvenanceDetectionMethod


def test_provider_metadata_has_priority_over_same_agency_byline():
    candidate = detect_agency_provenance(
        author="By Reuters",
        provider="Reuters",
    )

    assert candidate is not None
    assert candidate.source_slug == "reuters"
    assert (
        candidate.detection_method
        is ArticleProvenanceDetectionMethod.PROVIDER_METADATA
    )
    assert candidate.confidence == 0.95


def test_byline_matches_known_agency_alias_conservatively():
    candidate = detect_agency_provenance(
        author="Jane Doe (Associated Press)",
        provider=None,
    )

    assert candidate is not None
    assert candidate.source_slug == "associated-press"
    assert candidate.detection_method is ArticleProvenanceDetectionMethod.BYLINE
    assert candidate.confidence == 0.90


def test_conflicting_provider_and_byline_are_rejected():
    assert (
        detect_agency_provenance(
            author="Reuters",
            provider="Associated Press",
        )
        is None
    )


def test_unrelated_text_does_not_match_short_alias():
    assert (
        detect_agency_provenance(
            author="APA Research Group",
            provider=None,
        )
        is None
    )


def test_the_associated_press_alias_is_recognized():
    candidate = detect_agency_provenance(
        author="The Associated Press",
        provider=None,
    )

    assert candidate is not None
    assert candidate.source_slug == "associated-press"
    assert candidate.detection_method is ArticleProvenanceDetectionMethod.BYLINE
