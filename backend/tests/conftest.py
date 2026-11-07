import pytest

from app.config import get_settings
from app.main import app
from app.models import Konto
from app.services.auth import BEGRENZER, Inhaber, aktuelles_konto, inhaber

CSRF = {"X-Sponsorenkompass": "1"}
# Fachtests laufen mit Abo (alles freigeschaltet); Gast und Sperre prüft test_freigabe.py
TEST_KONTO = Konto(id=1, email="test@verein.example", passwort_hash="-", abo=True)


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
    monkeypatch.setattr(settings, "passwort_leckpruefung", False)  # kein Netz in Tests
    BEGRENZER.leeren()
    # Fachtests laufen als angemeldetes Testkonto 1; test_sicherheit.py prüft die echte Anmeldung
    app.dependency_overrides[aktuelles_konto] = lambda: TEST_KONTO
    app.dependency_overrides[inhaber] = lambda: Inhaber(konto=TEST_KONTO, gast_hash=None)
    yield settings
    get_settings.cache_clear()
