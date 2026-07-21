import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.analysis.normalization import normalize_name
from app.analysis.provider import ArticleAnalysisInput, EntityTopicAnalyzer
from app.analysis.resolver import EntityResolver, TopicResolver
from app.analysis.rule_based import RuleBasedEntityTopicAnalyzer
from app.models.article import Article
from app.models.entity import ArticleEntity
from app.models.topic import ArticleTopic
from app.repositories.entity_topic import EntityTopicRepository
from app.core.settings import settings


@dataclass(frozen=True, slots=True)
class AnalysisBatchResult:
    processed: int
    failed: int


class EntityTopicAnalysisService:
    def __init__(self, analyzer: EntityTopicAnalyzer | None = None, repository: EntityTopicRepository | None = None, *, min_entity_confidence: float | None = None, min_topic_confidence: float | None = None, max_topics: int | None = None) -> None:
        self.analyzer = analyzer or RuleBasedEntityTopicAnalyzer()
        self.repository = repository or EntityTopicRepository()
        self.entity_resolver = EntityResolver(self.repository, min_confidence=min_entity_confidence if min_entity_confidence is not None else settings.entity_topic_min_entity_confidence)
        self.topic_resolver = TopicResolver(self.repository, min_confidence=min_topic_confidence if min_topic_confidence is not None else settings.entity_topic_min_topic_confidence)
        self.max_topics = max_topics if max_topics is not None else settings.entity_topic_max_topics_per_article

    def analysis_hash(self, article: Article) -> str:
        payload = [article.normalized_title or "", article.normalized_text or "", article.language_code or "", self.analyzer.provider, self.analyzer.version]
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    def analyze_article(self, db: Session, article: Article) -> None:
        expected_hash = self.analysis_hash(article)
        if article.entity_topic_analysis_hash == expected_hash:
            return
        data = ArticleAnalysisInput(article.id, article.normalized_title or "", article.normalized_text or "", article.language_code, article.published_at, {"feed_id": str(article.feed_id)})
        result = self.analyzer.analyze(data)  # Results remain untouched if provider raises.
        self.repository.replace_article_results(db, article.id)
        seen_mentions: set[tuple] = set()
        for mention in result.entities:
            entity = self.entity_resolver.resolve(db, mention)
            key = (entity.id if entity else None, normalize_name(mention.mention_text), mention.start_offset, mention.end_offset)
            if entity is None or key in seen_mentions:
                continue
            seen_mentions.add(key)
            db.add(ArticleEntity(article_id=article.id, entity_id=entity.id, mention_text=mention.mention_text, normalized_mention=key[1], entity_type=mention.entity_type, start_offset=mention.start_offset, end_offset=mention.end_offset, sentence_index=mention.sentence_index, confidence=mention.confidence, salience=mention.salience, extraction_provider=self.analyzer.provider, extraction_version=self.analyzer.version))
        seen_topics = set()
        for detected in sorted(result.topics, key=lambda item: (-item.relevance, item.name)):
            if len(seen_topics) >= self.max_topics:
                break
            topic = self.topic_resolver.resolve(db, detected)
            if topic is None or topic.id in seen_topics:
                continue
            seen_topics.add(topic.id)
            db.add(ArticleTopic(article_id=article.id, topic_id=topic.id, relevance=detected.relevance, confidence=detected.confidence, detection_provider=self.analyzer.provider, detection_version=self.analyzer.version))
        article.entity_topic_analysis_hash = expected_hash
        article.entity_topic_analysis_version = self.analyzer.version
        article.entity_topic_analyzed_at = datetime.now(UTC)
        article.entity_topic_analysis_error = None
        db.flush()


class EntityTopicAnalysisRunner:
    def __init__(self, session_factory: sessionmaker[Session], service: EntityTopicAnalysisService | None = None) -> None:
        self.session_factory, self.service = session_factory, service or EntityTopicAnalysisService()

    def run_pending(self, *, limit: int) -> AnalysisBatchResult:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        processed = failed = 0
        with self.session_factory() as db:
            articles = self.service.repository.list_pending_articles(db, analysis_hash_for=self.service.analysis_hash, limit=limit)
            db.rollback()
            for article in articles:
                article_id = article.id
                try:
                    with db.begin():
                        current = db.get(Article, article_id, with_for_update=True)
                        if current is not None:
                            self.service.analyze_article(db, current)
                    processed += 1
                except Exception as exc:
                    db.rollback()
                    with db.begin():
                        current = db.get(Article, article_id)
                        if current is not None:
                            current.entity_topic_analysis_error = str(exc)[:2000]
                    failed += 1
        return AnalysisBatchResult(processed, failed)
