from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "YetSee API"
    app_version: str = "1.1.0"
    database_url: str = "sqlite:///./yetsee.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    auto_discovery_enabled: bool = False
    auto_discovery_interval_seconds: int = 3600
    auto_discovery_initial_delay_seconds: int = 30
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
