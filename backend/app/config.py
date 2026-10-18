"""Zentrale Konfiguration über Umgebungsvariablen (Präfix ``SOLARPILOT_``)."""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOLARPILOT_",
        env_file=(str(REPO_DIR / ".env"), str(BACKEND_DIR / ".env")),
        extra="ignore",
    )

    data_dir: Path = BACKEND_DIR / "data"
    database_url: str | None = None
    secret_key: str | None = None
    config_dir: Path = REPO_DIR / "config"
    sites_file: Path | None = None
    static_dir: Path | None = None
    demo: bool = False
    poll_interval_s: float = 10.0
    store_interval_s: int = 60
    scheduler_enabled: bool = True
    cors_origins: str = ""
    cookie_secure: bool = False
    retention_days: int = 730
    log_level: str = "INFO"
    http_timeout_s: float = 10.0

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'solarpilot.db').as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolved_secret(self) -> str:
        """Secret aus ENV, sonst aus ``data/secret.key`` (wird beim ersten Start erzeugt)."""
        if self.secret_key:
            return self.secret_key
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / "secret.key"
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        value = secrets.token_urlsafe(48)
        path.write_text(value, encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:  # pragma: no cover - Windows
            pass
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
