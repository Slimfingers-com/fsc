"""Public ready-analyses discovery is strictly German and generation-current."""

from app.enums.source_type import SourceType
from tests.coverage_helpers import build_complete_analysis_story


def specs(languages=("de", "de")):
    return [
        {
            "source_type": SourceType.NEWS,
            "claim_text": "The plan begins Monday.",
            "language_code": languages[0],
            "title": "Deutscher Bericht A" if languages[0].startswith("de") else "English report A",
        },
        {
            "source_type": SourceType.AGENCY,
            "claim_text": "The plan begins Monday.",
            "language_code": languages[1],
            "title": "Deutscher Bericht B" if languages[1].startswith("de") else "English report B",
        },
    ]


def test_ready_discovery_requires_two_german_sources_and_full_generations(client, db, monkeypatch):
    german = build_complete_analysis_story(db, specs=specs())
    foreign = build_complete_analysis_story(db, specs=specs(("en", "en")))
    mixed = build_complete_analysis_story(db, specs=specs(("de", "en")))
    unprocessed = build_complete_analysis_story(db, specs=specs())
    # Metadata changes invalidate this last StoryAnalysis generation.
    unprocessed["sources"][0].country = "DE"
    db.flush()

    from sqlalchemy import select
    from app.models.coverage import StoryCoverageSummary
    from app.api.story_analysis import service

    candidate = db.scalar(
        select(StoryCoverageSummary.story_id)
        .where(StoryCoverageSummary.story_id == german["story"].id)
    )
    assert candidate == german["story"].id, "coverage candidate missing"
    assert service.load(db, story_id=german["story"].id) is not None, (
        "German StoryAnalysis generation is not current"
    )
    detail_response = client.get(f"/stories/{german['story'].id}")
    assert detail_response.status_code == 200, detail_response.text
    assert len([
        a for a in detail_response.json()["articles"]
        if a["language_code"] == "de"
    ]) == 2, detail_response.json()["articles"]

    # Analyzing each foreign-only/mixed candidate was formerly expensive
    # and eventually timed out the public ready-discovery request.
    loaded_ids = []
    original_load = service.load

    def tracked_load(session, *, story_id):
        loaded_ids.append(story_id)
        return original_load(session, story_id=story_id)

    monkeypatch.setattr(service, "load", tracked_load)

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
    assert foreign["story"].id not in loaded_ids
    assert mixed["story"].id not in loaded_ids
    assert german["story"].id in loaded_ids



def test_ready_discovery_accepts_german_locale_variants(client, db):
    localized = build_complete_analysis_story(
        db, specs=specs(("de-AT", "de-CH"))
    )
    result = client.get("/analyses/ready")
    assert result.status_code == 200, result.text
    assert len(result.json()) == 1, result.text
    assert result.json()[0]["story_id"] == str(localized["story"].id)
    assert result.json()[0]["source_count"] == 2
    assert result.json()[0]["title"].startswith("Deutscher Bericht")


def test_ready_discovery_limit_is_bounded(client, db):
    build_complete_analysis_story(db, specs=specs())
    assert len(client.get("/analyses/ready?limit=1").json()) == 1
    assert client.get("/analyses/ready?limit=0").status_code == 422
    assert client.get("/analyses/ready?limit=100").status_code == 422
