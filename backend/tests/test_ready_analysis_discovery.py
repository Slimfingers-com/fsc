"""Public ready-analyses discovery is strictly German and generation-current."""

from app.enums.source_type import SourceType
from tests.coverage_helpers import build_complete_analysis_story


def specs(languages=("de", "de")):
    return [
        {
            "source_type": SourceType.NEWS,
            "claim_text": "The plan begins Monday.",
            "language_code": languages[0],
            "title": "Deutscher Bericht A" if languages[0] == "de" else "English report A",
        },
        {
            "source_type": SourceType.AGENCY,
            "claim_text": "The plan begins Monday.",
            "language_code": languages[1],
            "title": "Deutscher Bericht B" if languages[1] == "de" else "English report B",
        },
    ]


def test_ready_discovery_requires_two_german_sources_and_full_generations(client, db):
    german = build_complete_analysis_story(db, specs=specs())
    foreign = build_complete_analysis_story(db, specs=specs(("en", "en")))
    mixed = build_complete_analysis_story(db, specs=specs(("de", "en")))
    unprocessed = build_complete_analysis_story(db, specs=specs())
    # Metadata changes invalidate this last StoryAnalysis generation.
    unprocessed["sources"][0].country = "DE"
    db.flush()

    response = client.get("/analyses/ready")
    assert response.status_code == 200, response.text
    results = response.json()
    assert len(results) == 1, results
    row = results[0]
    assert row["story_id"] == str(german["story"].id)
    assert row["source_count"] == 2
    assert row["article_count"] == 2
    assert row["title"].startswith("Deutscher Bericht")
    assert row["last_article_at"]
    assert str(foreign["story"].id) not in response.text
    assert str(mixed["story"].id) not in response.text
    assert str(unprocessed["story"].id) not in response.text


def test_ready_discovery_limit_is_bounded(client, db):
    build_complete_analysis_story(db, specs=specs())
    assert len(client.get("/analyses/ready?limit=1").json()) == 1
    assert client.get("/analyses/ready?limit=0").status_code == 422
    assert client.get("/analyses/ready?limit=100").status_code == 422
