from sqlalchemy.engine import URL
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_host: str
    database_port: int
    database_name: str
    database_user: str
    database_password: str

    secret_key: str
    source_admin_api_key: str = ""

    gemini_api_key: str = ""
    openai_api_key: str = ""

    log_level: str = "INFO"
    feed_worker_poll_interval_seconds: float = 60.0
    feed_worker_batch_limit: int = 100
    feed_worker_claim_ttl_seconds: float = 300.0
    content_worker_poll_interval_seconds: float = 60.0
    content_worker_batch_limit: int = 100
    search_worker_poll_interval_seconds: float = 60.0
    search_worker_batch_limit: int = 100
    search_default_page_size: int = 20
    search_max_page_size: int = 100
    story_default_page_size: int = 20
    story_max_page_size: int = 100
    entity_topic_worker_poll_interval_seconds: float = 60.0
    entity_topic_worker_batch_limit: int = 100
    entity_topic_max_topics_per_article: int = 10
    entity_topic_min_entity_confidence: float = 0.65
    entity_topic_min_topic_confidence: float = 0.6
    entity_topic_worker_claim_ttl_seconds: float = 300.0
    entity_topic_retry_base_seconds: float = 30.0
    entity_topic_retry_max_seconds: float = 3600.0

    semantic_embedding_enabled: bool = False
    semantic_embedding_model: str = "text-embedding-3-small"
    semantic_embedding_timeout_seconds: float = 30.0
    semantic_embedding_max_article_characters: int = 12000
    semantic_embedding_worker_poll_interval_seconds: float = 60.0
    semantic_embedding_worker_batch_limit: int = 25
    semantic_embedding_worker_claim_ttl_seconds: float = 300.0
    semantic_embedding_retry_base_seconds: float = 30.0
    semantic_embedding_retry_max_seconds: float = 3600.0

    story_clustering_worker_poll_interval_seconds: float = 60.0
    story_clustering_worker_batch_limit: int = 100
    story_clustering_worker_claim_ttl_seconds: float = 300.0
    story_clustering_retry_base_seconds: float = 30.0
    story_clustering_retry_max_seconds: float = 3600.0
    story_clustering_window_hours: float = 48.0
    story_clustering_candidate_limit: int = 250
    story_clustering_min_similarity: float = 0.45
    story_clustering_semantic_similarity_threshold: float = 0.72

    claim_extraction_worker_poll_interval_seconds: float = 60.0
    claim_extraction_worker_batch_limit: int = 100
    claim_extraction_worker_claim_ttl_seconds: float = 300.0
    claim_extraction_retry_base_seconds: float = 30.0
    claim_extraction_retry_max_seconds: float = 3600.0
    claim_extraction_min_confidence: float = 0.6
    claim_extraction_max_claims_per_article: int = 30
    claim_default_page_size: int = 50
    claim_max_page_size: int = 200

    perspective_analysis_worker_poll_interval_seconds: float = 60.0
    perspective_analysis_worker_batch_limit: int = 100
    perspective_analysis_worker_claim_ttl_seconds: float = 300.0
    perspective_analysis_retry_base_seconds: float = 30.0
    perspective_analysis_retry_max_seconds: float = 3600.0
    perspective_analysis_min_confidence: float = 0.6
    perspective_default_page_size: int = 50
    perspective_max_page_size: int = 200

    claim_relation_worker_poll_interval_seconds: float = 60.0
    claim_relation_worker_batch_limit: int = 50
    claim_relation_worker_claim_ttl_seconds: float = 300.0
    claim_relation_retry_base_seconds: float = 30.0
    claim_relation_retry_max_seconds: float = 3600.0
    claim_relation_group_similarity_threshold: float = 0.82
    claim_relation_contradiction_similarity_threshold: float = 0.82
    claim_relation_default_page_size: int = 50
    claim_relation_max_page_size: int = 200

    evidence_worker_poll_interval_seconds: float = 60.0
    evidence_worker_batch_limit: int = 50
    evidence_worker_claim_ttl_seconds: float = 300.0
    evidence_retry_base_seconds: float = 30.0
    evidence_retry_max_seconds: float = 3600.0
    evidence_default_page_size: int = 50
    evidence_max_page_size: int = 200

    consensus_worker_poll_interval_seconds: float = 60.0
    consensus_worker_batch_limit: int = 50
    consensus_worker_claim_ttl_seconds: float = 300.0
    consensus_retry_base_seconds: float = 30.0
    consensus_retry_max_seconds: float = 3600.0
    consensus_minimum_independent_sources: int = 2
    consensus_default_page_size: int = 50
    consensus_max_page_size: int = 200

    coverage_worker_poll_interval_seconds: float = 60.0
    coverage_worker_batch_limit: int = 50
    coverage_worker_claim_ttl_seconds: float = 300.0
    coverage_retry_base_seconds: float = 30.0
    coverage_retry_max_seconds: float = 3600.0
    coverage_minimum_independent_content_sources: int = 2
    coverage_default_page_size: int = 50
    coverage_max_page_size: int = 200

    model_config = SettingsConfigDict(
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        return URL.create(
            "postgresql+psycopg",
            username=self.database_user,
            password=self.database_password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        ).render_as_string(
            hide_password=False
        )


settings = Settings()  # type: ignore[call-arg]
