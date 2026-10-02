from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select

from app.analysis.provider import (
    AnalysisResult,
    ArticleAnalysisInput,
    EntityMentionResult,
    EntityTopicAnalyzer,
    EntityType,
    TextPart,
    TopicResult,
)
from app.clustering.rule_based import RuleBasedStoryClusterer
from app.enums.source_type import SourceType
from app.ingestion.models import (
    FeedFormat,
    ParsedFeed,
    ParsedFeedEntry,
)
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.services.article_normalization import ArticleNormalizationRunner
from app.services.claim_extraction import ClaimExtractionRunner
from app.services.claim_relations import ClaimRelationRunner
from app.services.consensus import ConsensusRunner
from app.services.coverage import CoverageRunner
from app.services.entity_topic_analysis import (
    EntityTopicAnalysisRunner,
    EntityTopicAnalysisService,
)
from app.services.evidence import EvidenceRunner
from app.services.feed_persistence import FeedPersistenceService
from app.services.perspective_analysis import PerspectiveAnalysisRunner
from app.services.story_clustering import (
    StoryClusteringRunner,
    StoryClusteringService,
)
from tests.conftest import TestSessionLocal


class SharedCrossLanguageAnalyzer(EntityTopicAnalyzer):
    provider = "test-cross-language"
    version = "1"

    def analyze(
        self,
        article: ArticleAnalysisInput,
    ) -> AnalysisResult:
        entities = []
        for name, entity_type in (
            (
                "European Commission",
                EntityType.ORGANIZATION,
            ),
            (
                "Brussels",
                EntityType.LOCATION,
            ),
        ):
            start = article.normalized_text.index(name)
            entities.append(
                EntityMentionResult(
                    canonical_name=name,
                    mention_text=name,
                    entity_type=entity_type,
                    confidence=0.98,
                    salience=0.9,
                    text_source=TextPart.BODY,
                    start_offset=start,
                    end_offset=start + len(name),
                    sentence_index=0,
                )
            )

        return AnalysisResult(
            entities=tuple(entities),
            topics=(
                TopicResult(
                    name="European climate package",
                    relevance=0.95,
                    confidence=0.95,
                ),
            ),
        )


def _feed(
    db,
    *,
    token: str,
    country: str,
) -> Feed:
    source = Source(
        name=f"Source {token}",
        normalized_name=f"source {token}",
        slug=f"source-{token}",
        url=f"https://{token}.test",
        source_type=SourceType.NEWS,
        country=country,
    )
    feed = Feed(
        source=source,
        name="Main",
        url=f"https://{token}.test/feed",
    )
    db.add(feed)
    db.flush()
    return feed


def _parsed_feed(
    *,
    feed_url: str,
    language: str,
    external_id: str,
    title: str,
    content: str,
    published_at: datetime,
) -> ParsedFeed:
    return ParsedFeed(
        source_url=feed_url,
        format=FeedFormat.RSS,
        version="rss20",
        title="Cross-language acceptance feed",
        link=feed_url.removesuffix("/feed"),
        description="Acceptance fixture",
        language=language,
        updated_at=published_at,
        entries=(
            ParsedFeedEntry(
                external_id=external_id,
                title=title,
                link=(
                    feed_url.removesuffix("/feed")
                    + f"/articles/{external_id}"
                ),
                summary=None,
                content=content,
                author="FSC Test",
                published_at=published_at,
                updated_at=published_at,
                categories=(),
                enclosures=(),
            ),
        ),
        warnings=(),
    )


def _assert_batch(result, *, processed: int) -> None:
    assert result.processed == processed
    assert result.failed == 0


def test_multilingual_story_runs_from_ingestion_through_integrated_analysis(
    client,
):
    now = datetime(
        2026,
        10,
        2,
        10,
        0,
        tzinfo=UTC,
    )
    token = uuid4().hex

    german_body = (
        "Die European Commission hat heute in Brussels ein neues "
        "Klimapaket beschlossen. Das Paket enthält verbindliche Ziele "
        "für Energie, Verkehr und Industrie. Die Mitgliedstaaten "
        "beraten nun über die Umsetzung und den gemeinsamen Zeitplan."
    )
    english_body = (
        "The European Commission approved a new climate package in "
        "Brussels today. The package contains binding targets for "
        "energy, transport and industry. Member states will now "
        "discuss implementation and the common timetable."
    )

    with TestSessionLocal.begin() as db:
        de_feed = _feed(
            db,
            token=f"de-{token}",
            country="DE",
        )
        en_feed = _feed(
            db,
            token=f"en-{token}",
            country="GB",
        )

        persistence = FeedPersistenceService()
        de_result = persistence.persist(
            db,
            feed=de_feed,
            parsed_feed=_parsed_feed(
                feed_url=de_feed.url,
                language="de",
                external_id=f"de-{token}",
                title=(
                    "European Commission beschließt Klimapaket "
                    "in Brussels"
                ),
                content=german_body,
                published_at=now,
            ),
            fetched_at=now,
        )
        en_result = persistence.persist(
            db,
            feed=en_feed,
            parsed_feed=_parsed_feed(
                feed_url=en_feed.url,
                language="en",
                external_id=f"en-{token}",
                title=(
                    "European Commission approves climate package "
                    "in Brussels"
                ),
                content=english_body,
                published_at=now,
            ),
            fetched_at=now,
        )

        assert de_result.inserted == 1
        assert en_result.inserted == 1

    normalization = ArticleNormalizationRunner(
        TestSessionLocal,
        worker_id="multilingual-normalization",
    )
    normalization_result = normalization.run_pending(
        limit=10
    )
    assert normalization_result.processed == 2
    assert normalization_result.changed == 2
    assert normalization_result.unchanged == 0

    with TestSessionLocal() as db:
        articles = list(
            db.scalars(
                select(Article)
                .order_by(Article.language_code)
            ).all()
        )
        assert {
            article.language_code
            for article in articles
        } == {"de", "en"}
        article_ids = {
            article.language_code: article.id
            for article in articles
        }

    entity_topic = EntityTopicAnalysisRunner(
        TestSessionLocal,
        service=EntityTopicAnalysisService(
            analyzer=SharedCrossLanguageAnalyzer(),
        ),
        worker_id="multilingual-entity-topic",
    )
    _assert_batch(
        entity_topic.run_pending(limit=10),
        processed=2,
    )

    clustering = StoryClusteringRunner(
        TestSessionLocal,
        StoryClusteringService(
            clusterer=RuleBasedStoryClusterer(),
        ),
        worker_id="multilingual-story-clustering",
        window_hours=48.0,
        candidate_limit=250,
    )
    _assert_batch(
        clustering.run_pending(limit=10),
        processed=2,
    )

    with TestSessionLocal() as db:
        stories = list(
            db.scalars(
                select(Story).where(
                    Story.deleted_at.is_(None)
                )
            ).all()
        )
        assert len(stories) == 1
        story_id = stories[0].id
        assert stories[0].language_code == "mul"

        memberships = list(
            db.scalars(
                select(StoryArticle)
                .where(
                    StoryArticle.story_id == story_id,
                    StoryArticle.deleted_at.is_(None),
                )
                .order_by(StoryArticle.clustered_at)
            ).all()
        )
        assert len(memberships) == 2
        matched = [
            membership
            for membership in memberships
            if membership.match_kind == "matched"
        ]
        assert len(matched) == 1
        assert matched[0].match_details is not None
        assert (
            matched[0].match_details["cross_language"]
            is True
        )
        assert set(
            matched[0].match_details["language_pair"]
        ) == {"de", "en"}
        assert (
            "cross_language_entities"
            in matched[0].match_details["match_basis"]
        )

    claims = ClaimExtractionRunner(
        TestSessionLocal,
        worker_id="multilingual-claims",
    )
    _assert_batch(
        claims.run_pending(limit=10),
        processed=2,
    )

    perspectives = PerspectiveAnalysisRunner(
        TestSessionLocal,
        worker_id="multilingual-perspectives",
    )
    _assert_batch(
        perspectives.run_pending(limit=10),
        processed=2,
    )

    claim_relations = ClaimRelationRunner(
        TestSessionLocal,
        worker_id="multilingual-claim-relations",
    )
    _assert_batch(
        claim_relations.run_pending(limit=10),
        processed=1,
    )

    evidence = EvidenceRunner(
        TestSessionLocal,
        worker_id="multilingual-evidence",
    )
    _assert_batch(
        evidence.run_pending(limit=10),
        processed=1,
    )

    consensus = ConsensusRunner(
        TestSessionLocal,
        worker_id="multilingual-consensus",
    )
    _assert_batch(
        consensus.run_pending(limit=10),
        processed=1,
    )

    coverage = CoverageRunner(
        TestSessionLocal,
        worker_id="multilingual-coverage",
    )
    _assert_batch(
        coverage.run_pending(limit=10),
        processed=1,
    )

    story_response = client.get(
        f"/stories/{story_id}"
    )
    assert story_response.status_code == 200
    story_payload = story_response.json()
    assert story_payload["language_code"] == "mul"
    assert story_payload["article_count"] == 2
    assert {
        article["article_id"]
        for article in story_payload["articles"]
    } == {
        str(article_ids["de"]),
        str(article_ids["en"]),
    }
    assert {
        article["article_id"]: article["language_code"]
        for article in story_payload["articles"]
    } == {
        str(article_ids["de"]): "de",
        str(article_ids["en"]): "en",
    }

    analysis_response = client.get(
        f"/stories/{story_id}/analysis"
    )
    assert analysis_response.status_code == 200
    analysis_payload = analysis_response.json()
    assert analysis_payload["story_id"] == str(
        story_id
    )
    assert analysis_payload["coverage"][
        "article_count"
    ] == 2

    with TestSessionLocal() as db:
        assert {
            db.get(Article, article_id).language_code
            for article_id in article_ids.values()
        } == {"de", "en"}
        assert (
            db.scalar(
                select(func.count())
                .select_from(StoryArticle)
                .where(
                    StoryArticle.story_id == story_id,
                    StoryArticle.deleted_at.is_(None),
                )
            )
            == 2
        )
