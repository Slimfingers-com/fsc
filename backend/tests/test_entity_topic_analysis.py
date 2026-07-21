from datetime import UTC, datetime
from uuid import uuid4

from app.analysis.normalization import normalize_name, normalize_topic, stable_slug
from app.analysis.provider import ArticleAnalysisInput, EntityType
from app.analysis.rule_based import RuleBasedEntityTopicAnalyzer
from app.models.article import Article
from app.services.entity_topic_analysis import EntityTopicAnalysisService


def test_entity_name_normalization_is_case_and_whitespace_insensitive():
    assert normalize_name("  OpenAI,   Inc. ") == "openai inc"


def test_topic_normalization_merges_simple_plural_and_slug_is_stable():
    assert normalize_topic("Technologies") == "technology"
    assert stable_slug("Künstliche Intelligenz") == "kunstliche-intelligenz"


def test_rule_provider_recognizes_multi_part_people_and_organizations():
    result = RuleBasedEntityTopicAnalyzer().analyze(ArticleAnalysisInput(
        uuid4(), "Angela Dorothea Merkel besucht Berlin", "Angela Dorothea Merkel sprach mit Acme GmbH in Berlin. Acme GmbH entwickelt Systeme. Systeme helfen vielen Firmen.", "de", None,
    ))
    assert any(item.canonical_name == "Angela Dorothea Merkel" and item.entity_type == EntityType.PERSON for item in result.entities)
    assert any(item.canonical_name == "Acme GmbH" and item.entity_type == EntityType.ORGANIZATION for item in result.entities)
    assert any(item.entity_type == EntityType.LOCATION for item in result.entities)
    assert all(item.start_offset is not None and item.end_offset is not None for item in result.entities)


def test_analysis_hash_changes_with_text_and_analyzer_version():
    article = Article(id=uuid4(), feed_id=uuid4(), identity_type="guid", identity_key="x", normalized_title="Title", normalized_text="First", language_code="en")
    first = EntityTopicAnalysisService().analysis_hash(article)
    article.normalized_text = "Second"
    second = EntityTopicAnalysisService().analysis_hash(article)
    analyzer = RuleBasedEntityTopicAnalyzer()
    analyzer.version = "2.0.0"
    third = EntityTopicAnalysisService(analyzer=analyzer).analysis_hash(article)
    assert len({first, second, third}) == 3


def test_rule_provider_is_deterministic_and_topics_are_significant():
    data = ArticleAnalysisInput(uuid4(), "Climate Policy", "Climate policy shapes markets. Climate policy changes markets. Markets influence climate policy.", "en", datetime.now(UTC))
    analyzer = RuleBasedEntityTopicAnalyzer()
    assert analyzer.analyze(data) == analyzer.analyze(data)
    assert any("climate" in topic.name for topic in analyzer.analyze(data).topics)
    assert not any(topic.name in {"the", "and"} for topic in analyzer.analyze(data).topics)
