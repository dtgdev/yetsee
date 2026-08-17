from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "YetSee API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://yetsee:yetsee@postgres:5432/yetsee"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000"
    allow_manual_promotion: bool = True
    external_signal_topics: str = "running clubs,ai infrastructure,ai agents,home batteries"
    reddit_user_agent: str = "YetSee/0.3 (+https://yetsee.local)"
    reddit_results_per_topic: int = 10
    google_trends_geo: str = "US"
    google_trends_timeframe: str = "now 7-d"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def external_signal_topic_list(self) -> list[str]:
        return [item.strip() for item in self.external_signal_topics.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
