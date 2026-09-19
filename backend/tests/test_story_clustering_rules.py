from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.clustering.features import extract_title_terms
from app.clustering.provider import (
    StoryCandidate,
    StoryClusteringInput,
)
from app.clustering.rule_based import RuleBasedStoryClusterer


def make_article(
    *,
    title_terms=("berlin", "wahl"),
    entity_ids=(),
    topic_ids=(),
):
    return StoryClusteringInput(
        article_id=uuid4(),
        language_code="de",
        article_time=datetime(
            2026,
            9,
            19,
            10,
            0,
            tzinfo=UTC,
        ),
        title_terms=title_terms,
        entity_ids=entity_ids,
        topic_ids=topic_ids,
    )


def make_candidate(
    *,
    story_id=None,
    article_time=None,
    title_terms=("berlin", "wahl"),
    entity_ids=(),
    topic_ids=(),
):
    return StoryCandidate(
        story_id=story_id or uuid4(),
        membership_id=uuid4(),
        article_id=uuid4(),
        article_time=article_time
        or datetime(
            2026,
            9,
            19,
            9,
            0,
            tzinfo=UTC,
        ),
        title_terms=title_terms,
        entity_ids=entity_ids,
        topic_ids=topic_ids,
    )


def test_extract_title_terms_normalizes_deduplicates_and_sorts():
    assert extract_title_terms(
        "Berlin BERLIN Wahl!"
    ) == (
        "berlin",
        "wahl",
    )


def test_extract_title_terms_removes_stopwords_with_umlaut():
    assert extract_title_terms(
        "Für die Wahl in Berlin"
    ) == (
        "berlin",
        "wahl",
    )


def test_extract_title_terms_handles_empty_title():
    assert extract_title_terms(None) == ()
    assert extract_title_terms("") == ()


@pytest.mark.parametrize(
    "threshold",
    [-0.01, 1.01],
)
def test_rule_based_clusterer_rejects_invalid_threshold(
    threshold,
):
    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        RuleBasedStoryClusterer(
            min_similarity=threshold,
        )


def test_rule_based_clusterer_returns_no_match_without_candidates():
    clusterer = RuleBasedStoryClusterer()

    result = clusterer.cluster(
        make_article(),
        (),
    )

    assert result.story_id is None
    assert result.similarity_score == 0.0
    assert result.matched_membership_id is None
    assert result.matched_article_id is None
    assert result.details["candidate_count"] == 0


def test_rule_based_clusterer_matches_strong_title_overlap():
    clusterer = RuleBasedStoryClusterer()

    candidate = make_candidate(
        title_terms=("berlin", "wahl"),
    )

    result = clusterer.cluster(
        make_article(
            title_terms=("berlin", "wahl"),
        ),
        (candidate,),
    )

    assert result.story_id == candidate.story_id
    assert result.matched_membership_id == candidate.membership_id
    assert result.matched_article_id == candidate.article_id
    assert result.similarity_score == 1.0


def test_rule_based_clusterer_does_not_match_unrelated_candidate():
    clusterer = RuleBasedStoryClusterer()

    candidate = make_candidate(
        title_terms=("fussball", "muenchen"),
    )

    result = clusterer.cluster(
        make_article(
            title_terms=("berlin", "wahl"),
        ),
        (candidate,),
    )

    assert result.story_id is None
    assert result.similarity_score == 0.0


def test_rule_based_clusterer_prefers_higher_score():
    clusterer = RuleBasedStoryClusterer()

    lower = make_candidate(
        title_terms=("berlin", "wahl", "bundestag"),
    )
    higher = make_candidate(
        title_terms=("berlin", "wahl"),
    )

    result = clusterer.cluster(
        make_article(
            title_terms=("berlin", "wahl"),
        ),
        (
            lower,
            higher,
        ),
    )

    assert result.story_id == higher.story_id


def test_rule_based_clusterer_prefers_newer_candidate_on_score_tie():
    clusterer = RuleBasedStoryClusterer()

    older = make_candidate(
        article_time=datetime(
            2026,
            9,
            19,
            8,
            0,
            tzinfo=UTC,
        ),
    )
    newer = make_candidate(
        article_time=datetime(
            2026,
            9,
            19,
            9,
            0,
            tzinfo=UTC,
        ),
    )

    result = clusterer.cluster(
        make_article(),
        (
            older,
            newer,
        ),
    )

    assert result.story_id == newer.story_id


def test_rule_based_clusterer_uses_story_id_as_final_tiebreaker():
    clusterer = RuleBasedStoryClusterer()

    article_time = datetime(
        2026,
        9,
        19,
        9,
        0,
        tzinfo=UTC,
    )

    higher_story_id = UUID(
        "ffffffff-ffff-ffff-ffff-ffffffffffff"
    )
    lower_story_id = UUID(
        "00000000-0000-0000-0000-000000000001"
    )

    first = make_candidate(
        story_id=higher_story_id,
        article_time=article_time,
    )
    second = make_candidate(
        story_id=lower_story_id,
        article_time=article_time,
    )

    result = clusterer.cluster(
        make_article(),
        (
            first,
            second,
        ),
    )

    assert result.story_id == lower_story_id
