from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_host: str
    database_port: int
    database_name: str
    database_user: str
    database_password: str

    secret_key: str

    gemini_api_key: str = ""
    openai_api_key: str = ""

    log_level: str = "INFO"
    feed_worker_poll_interval_seconds: float = 60.0
    feed_worker_batch_limit: int = 100
    content_worker_poll_interval_seconds: float = 60.0
    content_worker_batch_limit: int = 100
    search_worker_poll_interval_seconds: float = 60.0
    search_worker_batch_limit: int = 100
    search_default_page_size: int = 20
    search_max_page_size: int = 100
    entity_topic_worker_poll_interval_seconds: float = 60.0
    entity_topic_worker_batch_limit: int = 100
    entity_topic_max_topics_per_article: int = 10
    entity_topic_min_entity_confidence: float = 0.65
    entity_topic_min_topic_confidence: float = 0.6

    model_config = SettingsConfigDict(
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.database_user}:"
            f"{self.database_password}@"
            f"{self.database_host}:"
            f"{self.database_port}/"
            f"{self.database_name}"
        )


settings = Settings()
