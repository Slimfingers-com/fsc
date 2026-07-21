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
