"""
Centralized application configuration.

All environment variables are loaded and validated here via Pydantic Settings.
No other module should read os.environ directly — import `settings` instead.
"""
import os
import subprocess
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _detect_git_sha() -> str:
    """Best-effort short commit SHA for /health and eval-report provenance.

    Checked in this order: GIT_COMMIT_SHA env var (set by CI/the Docker build
    — see .github/workflows/ci.yml and Dockerfile), then `git rev-parse`
    (works in local dev), else "unknown". Never raises — this is metadata,
    not something that should block startup.
    """
    env_sha = os.environ.get("GIT_COMMIT_SHA", "")
    if env_sha:
        return env_sha[:12]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, timeout=2, check=True,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "TechMart Support AI"
    app_version: str = "2.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Database
    mongo_uri: str
    mongo_db_name: str = "techmart_support"

    # LLM
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    llm_timeout_seconds: float = 20.0
    llm_max_retries: int = 3

    # Pricing for cost telemetry, USD per 1,000 tokens. These are *approximate*
    # figures entered by hand from the Gemini pricing page at the time this was
    # written, NOT fetched live — real-dollar numbers that drift out of date
    # are still more honest than a fabricated constant, but double-check
    # https://ai.google.dev/gemini-api/docs/pricing before trusting cost
    # figures in a real budget decision. Override via env without a code change.
    gemini_input_price_per_1k_usd: float = 0.075
    gemini_output_price_per_1k_usd: float = 0.30

    # Demo auth credential (Milestone 10 hardening) — a single fixed
    # username + bcrypt-hashed password, NOT a real user system. Good
    # enough to stop anonymous strangers from minting tokens against a
    # public deployment; not a substitute for real accounts.
    demo_username: str = "demo"
    demo_password_hash: str = ""

    # Rate limiting
    rate_limit_default: str = "60/minute"

    # Router version: "rule_based" | "llm_based" | "trained_classifier"
    active_router: str = "rule_based"

    # CORS — comma-separated in .env, parsed to a list here
    cors_allowed_origins_raw: str = Field(default="http://localhost:3000", validation_alias="CORS_ALLOWED_ORIGINS")

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins_raw.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def git_commit_sha(self) -> str:
        return _detect_git_sha()


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — .env is read once, not per-request."""
    return Settings()


settings = get_settings()
