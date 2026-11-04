from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # The shared .env lives in the repo root; a backend/.env, if present, overrides it.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_name: str = "MedBook"
    database_url: str = "postgresql+psycopg://medbook:medbook@localhost:5432/medbook"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]


# GoF Singleton: one Settings instance per process with a single global access point.
# Enforced by convention (always go through get_settings), which keeps it replaceable
# in tests via FastAPI dependency_overrides.
@lru_cache
def get_settings() -> Settings:
    return Settings()
