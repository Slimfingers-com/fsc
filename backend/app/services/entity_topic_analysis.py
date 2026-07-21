import hashlib
import json
import logging
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

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnalysisBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


class EntityTopicAnalysisService:
    CONFIG_VERSION = "1"

    def __init__(self, analyzer: EntityTopicAnalyzer | None = None, repository: EntityTopicRepository | None = None, *, min_entity_confidence: float = 0.65, min_topic_confidence: float = 0.6, max_topics: int = 10, config_version: str = CONFIG_VERSION) -> None:
        self.analyzer = analyzer or RuleBasedEntityTopicAnalyzer()
        self.repository = repository or EntityTopicRepository()
        self.entity_resolver = EntityResolver(self.repository, min_confidence=min_entity_confidence)
        self.topic_resolver = TopicResolver(self.repository, min_confidence=min_topic_confidence)
        self.max_topics = max_topics
        self.config_version = config_version

    def analysis_hash(self, article: Article) -> str:
        payload = [article.normalized_title or "", article.normalized_text or "", article.language_code or "", self.analyzer.provider, self.analyzer.version, self.config_version]
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    def analyze_article(self, db: Session, article: Article) -> bool:
        expected_hash = self.analysis_hash(article)
        if article.entity_topic_analysis_hash == expected_hash:
            return False
        data = ArticleAnalysisInput(article.id, article.normalized_title or "", article.normalized_text or "", article.language_code, article.published_at, {"feed_id": str(article.feed_id)})
        result = self.analyzer.analyze(data)  # Results remain untouched if provider raises.
        self.repository.replace_article_results(db, article.id)
        seen_mentions: set[tuple] = set()
        for mention in result.entities:
            source_text = (article.normalized_title or "") if mention.text_part.value == "title" else (article.normalized_text or "")
            if mention.start_offset is not None:
                if mention.end_offset is None or source_text[mention.start_offset:mention.end_offset] != mention.mention_text:
                    logger.warning("Ignoring mention with invalid offsets", extra={"article_id": str(article.id), "text_part": mention.text_part.value})
                    continue
            entity = self.entity_resolver.resolve(db, mention)
            key = (entity.id if entity else None, mention.text_part, normalize_name(mention.mention_text), mention.start_offset, mention.end_offset)
            if entity is None or key in seen_mentions:
                continue
            seen_mentions.add(key)
            db.add(ArticleEntity(article_id=article.id, entity_id=entity.id, mention_text=mention.mention_text, normalized_mention=key[2], entity_type=entity.entity_type, text_part=mention.text_part, start_offset=mention.start_offset, end_offset=mention.end_offset, sentence_index=mention.sentence_index, confidence=mention.confidence, salience=mention.salience, extraction_provider=self.analyzer.provider, extraction_version=self.analyzer.version))
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
        article.entity_topic_analysis_provider = self.analyzer.provider
        article.entity_topic_analysis_config_version = self.config_version
        article.entity_topic_analysis_content_hash = article.content_hash
        article.entity_topic_analysis_normalization_version = article.normalization_version
        article.entity_topic_analyzed_at = datetime.now(UTC)
        article.entity_topic_analysis_error = None
        db.flush()
        return True


class EntityTopicAnalysisRunner:
    def __init__(self, session_factory: sessionmaker[Session], service: EntityTopicAnalysisService | None = None) -> None:
        self.session_factory, self.service = session_factory, service or EntityTopicAnalysisService()

    def run_pending(self, *, limit: int) -> AnalysisBatchResult:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        processed = skipped = failed = 0
        with self.session_factory() as db:
            articles = self.service.repository.list_pending_articles(db, provider=self.service.analyzer.provider, version=self.service.analyzer.version, config_version=self.service.config_version, limit=limit)
            article_ids = [article.id for article in articles]
            db.rollback()
            for article_id in article_ids:
                try:
                    with db.begin():
                        current = db.get(Article, article_id, with_for_update=True)
                        if current is not None:
                            if self.service.analyze_article(db, current):
                                processed += 1
                            else:
                                skipped += 1
                except Exception as exc:
                    db.rollback()
                    with db.begin():
                        current = db.get(Article, article_id)
                        if current is not None:
                            current.entity_topic_analysis_error = str(exc)[:2000]
                    failed += 1
                    logger.exception("Entity/topic article analysis failed", extra={"article_id": str(article_id), "provider": self.service.analyzer.provider, "version": self.service.analyzer.version})
        return AnalysisBatchResult(len(article_ids), processed, skipped, failed)
