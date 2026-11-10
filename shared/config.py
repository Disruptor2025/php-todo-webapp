"""App settings, read from environment variables / the .env file.

Usage:
    from shared.config import get_settings
    settings = get_settings()
    key = settings.require("GOOGLE_PLACES_API_KEY")
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": other variables in .env don't cause errors
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Secrets default to "" so the app can start (and tests can run) without them.
    # Code that needs one calls settings.require(...) for a clear error message.
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_PLACES_API_KEY: str = ""

    CLAUDE_MODEL: str = "claude-opus-5-5"
    PLACES_COST_PER_REQUEST_USD: float = 0.035
    ENRICH_COST_PER_LEAD_USD: float = 0.03

    CORS_ORIGINS: str = "http://localhost:4321"
    SITE_URL: str = "http://localhost:4321"

    def require(self, name: str) -> str:
        value = getattr(self, name)
        if not value:
            raise RuntimeError(f"{name} is not set. Add it to your .env file.")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse them (lru_cache remembers the result)."""
    return Settings()
