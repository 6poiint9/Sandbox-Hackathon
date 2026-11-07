"""Realistisches Potenzial (Marktwert aus Mitgliedern), Ziel-Vorschlag und lokale Demo-Anmeldung."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import InventarPosten, Konto, Verein
from app.services.auth import aktuelles_konto, inhaber
from app.services.potenzial import berechnen, marktwert

CSRF = {"X-Sponsorenkompass": "1"}


def test_marktwert_aus_mitgliedern_und_spielklasse():
    assert marktwert(Verein(name="FC", ort="O", mitglieder=300, spielklasse="Kreisliga")) == (2400, 6500)
    assert marktwert(Verein(name="FC", ort="O", mitglieder=300, spielklasse="Landesliga")) == (3900, 10500)
    assert marktwert(Verein(name="FC", ort="O")) is None


def test_potenzial_wird_auf_marktwert_begrenzt_theoretisch_bleibt_sichtbar():
    v = Verein(id=1, name="FC", ort="O", spielklasse="Kreisliga", mitglieder=300)
    viel = [InventarPosten(verein_id=1, katalog_id=k) for k in
            ("namensrecht_platz", "anzeigetafel", "trikot_brust", "vereinsbus", "bande", "azubi")]
    p = berechnen(v, viel, [])
    assert p.theoretisch_max > 8125
    assert p.spanne_max == 8100  # 6.500 × 1,25, auf 100 gerundet
    assert p.spanne_min <= 2400 and p.marktwert_min == 2400
    assert any("Marktwert" in a for a in p.annahmen)

    ohne_mitglieder = berechnen(Verein(id=1, name="FC", ort="O", spielklasse="Kreisliga"), viel, [])
    assert ohne_mitglieder.spanne_max == ohne_mitglieder.theoretisch_max  # ohne Mitglieder keine Grenze


def test_ohne_angebot_nur_standardpakete_und_jugendteams_aus_profil():
    v = Verein(id=1, name="FC", ort="O", spielklasse="Kreisliga", jugend_anzahl=4)
    p = berechnen(v, [], [])
    ids = {x.katalog_id for x in p.freie_pakete}
    assert "namensrecht_platz" not in ids and "bande" in ids
    jugend = berechnen(v, [InventarPosten(verein_id=1, katalog_id="trikot_jugend")], [])
    assert jugend.freie_pakete[0].menge == 4


def test_ziel_vorschlag_endpunkt():
    with TestClient(app, base_url="https://testserver", headers=CSRF) as c:
        r = c.get("/richtwerte/ziel", params={"mitglieder": 300, "spielklasse": "Kreisliga"}).json()
        assert (r["min"], r["max"], r["vorschlag"]) == (2400, 6500, 4500)
        assert c.get("/richtwerte/ziel", params={"mitglieder": 0}).status_code == 422


@pytest.fixture
def echte_anmeldung(isolierter_cache):
    app.dependency_overrides.pop(aktuelles_konto, None)
    app.dependency_overrides.pop(inhaber, None)
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(Konto(email="demo@verein.example", passwort_hash="-", abo=True))
        s.commit()

    def override():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield isolierter_cache
    app.dependency_overrides.clear()


def test_demo_anmeldung_nur_mit_einstellung_und_nur_von_localhost(echte_anmeldung, monkeypatch):
    lokal = TestClient(app, base_url="https://testserver", client=("127.0.0.1", 5000))
    fremd = TestClient(app, base_url="https://testserver", client=("203.0.113.7", 5000))
    assert lokal.get("/konto/ich").status_code == 401  # Standard: aus

    monkeypatch.setattr(echte_anmeldung, "demo_anmeldung_email", "demo@verein.example")
    r = lokal.get("/konto/ich")
    assert r.status_code == 200 and r.json()["abo"] is True
    assert fremd.get("/konto/ich").status_code == 401  # nie von außen
