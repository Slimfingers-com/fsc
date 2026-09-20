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

    story_clustering_worker_poll_interval_seconds: float = 60.0
    story_clustering_worker_batch_limit: int = 100
    story_clustering_worker_claim_ttl_seconds: float = 300.0
    story_clustering_retry_base_seconds: float = 30.0
    story_clustering_retry_max_seconds: float = 3600.0
    story_clustering_window_hours: float = 48.0
    story_clustering_candidate_limit: int = 250
    story_clustering_min_similarity: float = 0.45

    claim_extraction_worker_poll_interval_seconds: float = 60.0
    claim_extraction_worker_batch_limit: int = 100
    claim_extraction_worker_claim_ttl_seconds: float = 300.0
    claim_extraction_retry_base_seconds: float = 30.0
    claim_extraction_retry_max_seconds: float = 3600.0
    claim_extraction_min_confidence: float = 0.6
    claim_extraction_max_claims_per_article: int = 30
    claim_default_page_size: int = 50
    claim_max_page_size: int = 200

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
