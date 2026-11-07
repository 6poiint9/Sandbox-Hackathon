"""Einstellungen aus Umgebungsvariablen bzw. backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    exa_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    llm_analyse_provider: str = "gemini"
    llm_analyse_model: str = ""
    llm_text_provider: str = "anthropic"
    llm_text_model: str = "claude-sonnet-5-5"

    demo_mode: bool = False
    frontend_url: str = "http://localhost:5173"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'sponsorenkompass.db').as_posix()}"
    cache_dir: Path = BACKEND_DIR / "cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()
