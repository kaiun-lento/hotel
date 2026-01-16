from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Values are loaded from environment variables and optional .env file.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # App
    app_name: str = "Banquet Reservation App"
    environment: str = "dev"  # dev|staging|prod
    api_prefix: str = "/api"

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/banquet"

    # Security / JWT
    secret_key: str = "CHANGE_ME"  # change in prod
    access_token_exp_minutes: int = 60
    jwt_algorithm: str = "HS256"

    # Password hashing
    bcrypt_rounds: int = 12

    # Email (SMTP)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    email_from: str = "no-reply@example.com"

    # Public base URL used in emails
    public_base_url: str = "http://localhost:3000"

    # CAPTCHA (optional)
    captcha_provider: str = ""  # "hcaptcha" | "recaptcha" | "turnstile" | ""
    captcha_secret_key: str = ""

    # Rate limiting
    rate_limit_enabled: bool = True

    # Timezone
    timezone: str = "Asia/Tokyo"


@lru_cache
def get_settings() -> Settings:
    return Settings()
