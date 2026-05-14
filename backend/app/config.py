from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: str = Field(default="development", description="development | staging | production")
    log_level: str = Field(default="INFO")

    # CORS
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # Cookies / session
    session_secret: str = Field(
        default="dev-only-do-not-use-in-prod",
        description="Used to sign anonymous session cookies",
    )
    cookie_name: str = Field(default="tt_session")
    cookie_secure: bool = Field(default=False)  # True in prod (HTTPS)

    # Limits
    max_prompt_chars: int = Field(default=100_000)
    rate_limit_per_minute: int = Field(default=100)

    # Closed-tokenizer proxies (optional — endpoints disabled if missing)
    anthropic_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)

    # Cost guardrails: cap paid `count_tokens` calls per day
    paid_count_daily_cap: int = Field(default=10_000)

    # PostHog (server-side analytics; optional)
    posthog_api_key: str | None = Field(default=None)
    posthog_host: str = Field(default="https://us.i.posthog.com")


@lru_cache
def get_settings() -> Settings:
    return Settings()
