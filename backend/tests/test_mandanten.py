"""Mandantentrennung: Jedes Konto ist ein Mandant. Zwei automatische Garantien:

1. Kein Endpunkt ohne Schutz: Jede Route ist entweder ausdrücklich öffentlich
   (Liste unten) oder hängt an `zugriff`/`aktuelles_konto`. Ein neuer Endpunkt
   ohne Schutz lässt diesen Test scheitern.
2. Kein Zugriff über Mandantengrenzen: Mandant B ruft JEDEN Endpunkt mit JEDER
   Methode und den IDs von Mandant A auf – keine einzige Erfolgsantwort.
"""

import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db import get_session
from app.main import app
from app.models import Ansprache, Kandidat, Unternehmen
from app.services.auth import aktuelles_konto, inhaber, zugriff

CSRF = {"X-Sponsorenkompass": "1"}
PW_A = "mandant-a-" + "lange-testphrase"
PW_B = "mandant-b-" + "lange-testphrase"

# Ausdrücklich öffentlich – enthalten keine Mandantendaten.
OEFFENTLICH = {
    ("GET", "/health"),
    ("GET", "/katalog"),
    ("POST", "/interessenten"),
    ("GET", "/interessenten/anzahl"),
    ("POST", "/konto/registrieren"),
    ("POST", "/konto/anmelden"),
    ("POST", "/konto/abmelden"),
}


def alle_routen() -> list:
    routen = []
    for r in app.routes:
        if isinstance(r, APIRoute):
            routen.append(r)
        elif hasattr(r, "effective_route_contexts"):
            routen.extend(r.effective_route_contexts())
    return routen


def abhaengigkeiten(dependant) -> set:
    namen = {dependant.call} if dependant.call else set()
    for d in dependant.dependencies:
        namen |= abhaengigkeiten(d)
    return namen


def test_jeder_endpunkt_ist_geschuetzt_oder_ausdruecklich_oeffentlich():
    ungeschuetzt = []
    for r in alle_routen():
        for methode in r.methods:
            if (methode, r.path) in OEFFENTLICH:
                continue
            aufrufe = abhaengigkeiten(r.dependant)
            if zugriff not in aufrufe and aktuelles_konto not in aufrufe:
                ungeschuetzt.append(f"{methode} {r.path}")
    assert ungeschuetzt == [], f"Endpunkte ohne Mandantenschutz: {ungeschuetzt}"


@pytest.fixture
def zwei_mandanten():
    app.dependency_overrides.pop(aktuelles_konto, None)
    app.dependency_overrides.pop(inhaber, None)
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)

    def override():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = override
    a = TestClient(app, base_url="https://testserver", headers=CSRF)
    b = TestClient(app, base_url="https://testserver", headers=CSRF)
    a.__enter__()
    b.__enter__()
    assert a.post("/konto/registrieren", json={"email": "a@verein-a.example", "passwort": PW_A}).status_code == 200
    assert b.post("/konto/registrieren", json={"email": "b@verein-b.example", "passwort": PW_B}).status_code == 200

    # Mandant A: vollständiger Datensatz über alle Objektarten
    vid = a.post("/vereine", json={"name": "FC A", "ort": "A-Stadt"}).json()["id"]
    sid = a.post(f"/vereine/{vid}/sponsoren", json=[{"firma": "Geheimer Sponsor A", "betrag_eur": 5000}]).json()[0]["id"]
    asset = a.post(f"/vereine/{vid}/assets", json={"katalog_id": "bande", "anzahl": 5}).json()[0]
    vergabe = a.post(f"/assets/{asset['id']}/vergaben", json={"sponsor_id": sid, "anzahl": 1}).json()[0]["vergaben"][0]["id"]
    with Session(eng) as s:
        s.add(Unternehmen(id=1, osm_id="n/1", name="Betrieb", branche="Handel", lat=0, lon=0))
        s.add(Kandidat(id=1, verein_id=vid, unternehmen_id=1, entfernung_km=1, vorfilter_score=50,
                       recherche_status="fertig", notiz="vertraulich A"))
        s.add(Ansprache(kandidat_id=1, brief="Brief A", leitfaden="-", email_betreff="-", email_text="-"))
        s.commit()
    akt = a.post(f"/vereine/{vid}/aktivitaeten", json={"art": "notiz", "text": "intern A", "sponsor_id": sid}).json()["id"]
    ids = {"verein_id": vid, "sponsor_id": sid, "asset_id": asset["id"], "vergabe_id": vergabe,
           "kandidat_id": 1, "aktivitaet_id": akt}
    yield a, b, ids, eng
    a.__exit__(None, None, None)
    b.__exit__(None, None, None)
    app.dependency_overrides.clear()


def test_mandant_b_erreicht_nichts_von_mandant_a(zwei_mandanten):
    a, b, ids, eng = zwei_mandanten
    geprueft = 0
    lecks = []
    for r in alle_routen():
        platzhalter = re.findall(r"{(\w+)}", r.path)
        if not platzhalter:
            continue  # Routen ohne ID zeigen nur eigene Daten (separat geprüft)
        pfad = r.path
        for p in platzhalter:
            pfad = pfad.replace("{" + p + "}", str(ids[p]))
        for methode in r.methods:
            antwort = b.request(methode, pfad, json={})
            geprueft += 1
            if antwort.status_code < 300 or "A" in antwort.text and ("Geheimer" in antwort.text or "vertraulich" in antwort.text):
                lecks.append(f"{methode} {pfad} -> {antwort.status_code}")
    assert geprueft >= 30
    assert lecks == [], f"Zugriff über Mandantengrenzen: {lecks}"

    # Listen ohne ID zeigen B nur eigene Daten
    assert b.get("/konto/vereine").json() == []

    # A's Daten sind unverändert (B konnte nichts schreiben oder löschen)
    sponsor = a.get(f"/vereine/{ids['verein_id']}/sponsoren").json()[0]
    assert sponsor["firma"] == "Geheimer Sponsor A" and sponsor["betrag_eur"] == 5000
    assert len(a.get(f"/vereine/{ids['verein_id']}/aktivitaeten").json()) >= 1
    with Session(eng) as s:
        assert s.exec(select(Kandidat)).one().notiz == "vertraulich A"
