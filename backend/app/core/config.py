from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

BACKEND_DIR = Path(__file__).resolve().parents[2]

APP_NAME = "VisoNarc"
APP_FULL_NAME = "VisoNarc – Drug Detection Using Voice and Motion"
APP_VERSION = "0.1.0"

MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str | None = Field(default=None, repr=False)
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "visonarc"
    db_user: str = "visonarc_app"
    db_password: str = Field(default="", repr=False)

    jwt_secret_key: str = Field(default="", repr=False)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "visonarc"
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)
    login_max_failed_attempts: int = Field(default=5, ge=1, le=50)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440)
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)

    store_raw_media: bool = False
    data_retention_days: int = Field(default=90, ge=1, le=3650)
    # Automatic deletion of sessions past retain_until. Off unless explicitly enabled in backend/.env.
    retention_auto_purge: bool = False
    retention_purge_interval_hours: int = Field(default=24, ge=1, le=720)
    # Per-IP limit on failed sign-ins (in addition to per-account lockout). Uses the TCP peer
    # address only; X-Forwarded-For is never trusted.
    login_ip_max_failures: int = Field(default=20, ge=1, le=1000)
    login_ip_window_seconds: int = Field(default=300, ge=10, le=86400)
    # Experimental screening. "off" (default): no estimate is ever computed. "synthetic_demo": a
    # fixed, documented demonstration formula runs on sessions flagged is_synthetic only.
    # There is no validated model, so no mode produces estimates for real sessions.
    screening_mode: Literal["off", "synthetic_demo"] = "off"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )

    def validate_for_startup(self) -> None:
        """Fail fast on insecure configuration instead of running with weak defaults."""
        secret = self.jwt_secret_key
        if len(secret) < MIN_JWT_SECRET_LENGTH or secret.startswith("replace-with"):
            raise RuntimeError(
                "JWT_SECRET_KEY is missing or too short. Run scripts\\bootstrap.ps1 "
                "or set a random value of at least 32 characters in backend/.env."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
