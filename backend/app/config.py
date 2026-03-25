from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Polymarket RV Scanner"
    # Host-side backend runs connect to the Dockerized Postgres instance via the published port.
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/polymarket_arb"
    polymarket_api_base_url: str = "https://gamma-api.polymarket.com"
    polymarket_page_size: int = 100
    polymarket_max_pages: int = 10
    market_scan_limit: int = 50
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_batch_size: int = 8
    frontend_origin: str = "http://localhost:5173"
    request_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
