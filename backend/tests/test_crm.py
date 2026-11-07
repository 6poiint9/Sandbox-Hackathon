"""CRM: Sponsoren pflegen, Verlauf, Aufgaben, Assets mit Vergaben, Übernahme nach Zusage."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import Kandidat, Unternehmen, Verein


@pytest.fixture
def c():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(Verein(id=1, name="FC", ort="O", spielklasse="Bezirksliga"))
        s.add(Unternehmen(id=1, osm_id="n/1", name="Bäckerei Müller", branche="Bäckereien", lat=0, lon=0))
        s.add(Kandidat(id=1, verein_id=1, unternehmen_id=1, entfernung_km=1, vorfilter_score=80, score=80,
                       recherche_status="fertig", paket_empfehlung={"katalog_ids": ["bande"], "namen": ["Bandenwerbung"]}))
        s.commit()

    def override():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_sponsor_bearbeiten_mit_verlauf_und_aufgaben(c):
    sid = c.post("/vereine/1/sponsoren", json=[{"firma": "Autohaus X"}]).json()[0]["id"]
    bald = (date.today() + timedelta(days=30)).isoformat()
    s = c.patch(f"/sponsoren/{sid}", json={"betrag_eur": 2500, "laufzeit_bis": bald, "email": "info@x.example",
                                           "status": "verlaengerung", "wiedervorlage": date.today().isoformat(),
                                           "naechster_schritt": "Angebot schicken"}).json()
    assert s["betrag_eur"] == 2500 and s["status"] == "verlaengerung"
    assert c.patch(f"/sponsoren/{sid}", json={"status": "quatsch"}).status_code == 422
    c.post("/vereine/1/aktivitaeten", json={"art": "anruf", "text": "Mit Chef telefoniert", "sponsor_id": sid})
    verlauf = c.get(f"/vereine/1/aktivitaeten?sponsor_id={sid}").json()
    assert [a["art"] for a in verlauf] == ["anruf", "status"]
    arten = sorted(a["art"] for a in c.get("/vereine/1/aufgaben").json())
    assert arten == ["vertragsende", "wiedervorlage"]


def test_assets_mit_einheiten_und_potenzial(c):
    sid = c.post("/vereine/1/sponsoren", json=[{"firma": "Autohaus X"}]).json()[0]["id"]
    assets = c.post("/vereine/1/assets", json={"katalog_id": "bande", "anzahl": 10, "preis_eur": 500}).json()
    aid = assets[0]["id"]
    assets = c.post(f"/assets/{aid}/vergaben", json={"sponsor_id": sid, "anzahl": 4, "preis_eur": 2000}).json()
    a = assets[0]
    assert (a["anzahl"], a["belegt"], a["frei"], a["einnahmen_eur"]) == (10, 4, 6, 2000)
    assert c.post(f"/assets/{aid}/vergaben", json={"sponsor_id": sid, "anzahl": 7}).status_code == 422
    p = c.get("/vereine/1/potenzial").json()
    bande = next(x for x in p["freie_pakete"] if x["katalog_id"] == "bande")
    assert bande["min"] == 3000 and bande["einheiten_frei"] == 6  # 6 freie Banden × 500 €


def test_kandidat_crm_und_uebernahme(c):
    k = c.patch("/kandidaten/1", json={"ansprechpartner": "Frau Müller", "telefon": "0761 1"}).json()
    assert k["ansprechpartner"] == "Frau Müller"
    aid = c.post("/vereine/1/assets", json={"katalog_id": "bande", "anzahl": 5}).json()[0]["id"]
    s = c.post("/kandidaten/1/zum-sponsor", json={"betrag_eur": 800, "asset_id": aid}).json()
    assert s["firma"] == "Bäckerei Müller" and s["ansprechpartner"] == "Frau Müller"
    assert s["gegenleistung"] == "bande"
    kand = c.get("/vereine/1/kandidaten").json()[0]
    assert kand["status"] == "zusage" and kand["sponsor_id"] == s["id"]
    assert c.get("/vereine/1/assets").json()[0]["belegt"] == 1
    # zweiter Klick legt keinen zweiten Sponsor an
    assert c.post("/kandidaten/1/zum-sponsor", json={}).json()["id"] == s["id"]


def test_landing_anmeldung(c):
    assert c.post("/interessenten", json={"email": "falsch"}).status_code == 422
    z = c.post("/interessenten", json={"email": "Vorstand@FC.example", "verein": "FC", "pilot": True}).json()
    assert z == {"anmeldungen": 1, "pilotvereine": 1}
    z = c.post("/interessenten", json={"email": "vorstand@fc.example", "rolle": "Kassenwart"}).json()
    assert z["anmeldungen"] == 1  # keine Dopplung


def test_konto_registrieren_anmelden_und_zugriffsschutz(c):
    pw = "test-" + "passwort-1"  # Testwert nur für diesen Test
    r = c.post("/konto/registrieren", json={"email": "Kasse@FC.example", "passwort": pw, "name": "Kasse"})
    assert r.status_code == 200
    token = r.json()["token"]
    kopf = {"Authorization": f"Bearer {token}"}
    assert c.post("/konto/registrieren", json={"email": "kasse@fc.example", "passwort": pw}).status_code == 409
    assert c.post("/konto/registrieren", json={"email": "x@fc.example", "passwort": "kurz"}).status_code == 422
    assert c.post("/konto/anmelden", json={"email": "kasse@fc.example", "passwort": "falsch-falsch"}).status_code == 401
    assert c.post("/konto/anmelden", json={"email": "kasse@fc.example", "passwort": pw}).status_code == 200

    # Verein 1 ohne Konto ist frei zugänglich, bis er übernommen wird
    assert c.get("/vereine/1").status_code == 200
    assert [v["id"] for v in c.post("/konto/vereine/1", headers=kopf).json()] == [1]
    assert c.get("/vereine/1").status_code == 401
    assert c.get("/vereine/1/kandidaten").status_code == 401
    assert c.get("/vereine/1", headers=kopf).status_code == 200

    # neues Konto sieht fremden Verein nicht
    fremd = c.post("/konto/registrieren", json={"email": "andere@fc.example", "passwort": pw}).json()["token"]
    assert c.get("/vereine/1", headers={"Authorization": f"Bearer {fremd}"}).status_code == 403
    # angemeldet angelegter Verein gehört direkt zum Konto
    neu = c.post("/vereine", json={"name": "SV", "ort": "O"}, headers=kopf).json()
    assert {v["id"] for v in c.get("/konto/vereine", headers=kopf).json()} == {1, neu["id"]}
    c.post("/konto/abmelden", headers=kopf)
    assert c.get("/konto/ich", headers=kopf).status_code == 401
