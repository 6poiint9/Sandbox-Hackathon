import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def isolierter_cache(tmp_path, monkeypatch):
    """Jeder Test bekommt einen eigenen Cache-Ordner und keinen echten Key."""
    get_settings.cache_clear()
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("DEMO_MODE", "0")
    settings = get_settings()
    monkeypatch.setattr(settings, "cache_dir", tmp_path)
    monkeypatch.setattr(settings, "google_cloud_project", "")  # Tests nie gegen Google
    monkeypatch.setattr(settings, "google_api_key", "")
    yield settings
    get_settings.cache_clear()
