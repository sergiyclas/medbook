from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # The shared .env lives in the repo root; a backend/.env, if present, overrides it.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_name: str = "MedBook"
    database_url: str = "postgresql+psycopg://medbook:medbook@localhost:5433/medbook"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    clinic_timezone: str = "Europe/Kyiv"
    clinic_name: str = "Клініка MedBook"
    # Public address of the web UI, used for links in e-mails
    app_url: str = "http://localhost:8080"

    # Must be overridden outside local demo use
    jwt_secret: str = "dev-only-secret-change-me-before-deploying"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 8 * 60

    # console – messages are only written to the worker log; nothing leaves the system.
    # live – real e-mail over SMTP and real SMS through Twilio; both must be configured.
    notification_mode: Literal["console", "live"] = "console"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    mail_from: str = ""  # defaults to smtp_username
    twilio_account_sid: str = ""
    twilio_auth_token: SecretStr = SecretStr("")
    twilio_from_number: str = ""

    worker_interval_seconds: int = 15
    notification_max_attempts: int = 5


# GoF Singleton: one Settings instance per process with a single global access point.
# Enforced by convention (always go through get_settings), which keeps it replaceable
# in tests via FastAPI dependency_overrides.
@lru_cache
def get_settings() -> Settings:
    return Settings()
