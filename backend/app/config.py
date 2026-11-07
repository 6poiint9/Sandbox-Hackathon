"""Einstellungen aus Umgebungsvariablen bzw. backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Beide Orte sind erlaubt; backend/.env gewinnt, wenn ein Wert doppelt gesetzt ist.
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # leere Zeilen wie "EXA_API_KEY=" überschreiben nichts
        extra="ignore",
    )

    exa_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # Gemini über Vertex AI mit Google-Login (ADC) oder über GEMINI_API_KEY.
    google_genai_use_vertexai: bool = False
    google_cloud_project: str = ""
    google_cloud_location: str = "global"
    google_api_key: str = ""  # Vertex-Express-Modus bzw. Places per API-Key

    # Modellnamen aus der Vertex-Modellliste vom 07.11.2026 (models.list()).
    llm_analyse_provider: str = "gemini"
    llm_analyse_model: str = "gemini-3.8-flash"
    llm_text_provider: str = "gemini"  # "anthropic" nur mit ANTHROPIC_API_KEY
    llm_text_model: str = "gemini-3.8-flash"

    demo_mode: bool = False
    frontend_url: str = "http://localhost:5173"

    # E-Mail-Benachrichtigung (optional). Ohne SMTP_HOST ist die Funktion aus.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_benutzer: str = ""
    smtp_passwort: str = ""
    smtp_absender: str = ""
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'sponsorenkompass.db').as_posix()}"
    cache_dir: Path = BACKEND_DIR / "cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()
