"""Phase 3: OSM-Auswertung, Vorfilter, Lücken und API (Netz gemockt)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.services import osm, vorfilter
from app.services.osm import Betrieb

VEREIN = (48.12, 7.85)

ELEMENTE = [
    {"type": "node", "id": 1, "lat": 48.121, "lon": 7.851,
     "tags": {"name": "Bäckerei Müller", "shop": "bakery", "website": "baeckerei-mueller.de"}},
    # Duplikat als Gebäude mit center
    {"type": "way", "id": 2, "center": {"lat": 48.1211, "lon": 7.8511},
     "tags": {"name": "Bäckerei Müller", "shop": "bakery", "addr:street": "Hauptstr.", "addr:housenumber": "3"}},
    {"type": "node", "id": 3, "lat": 48.13, "lon": 7.86,
     "tags": {"name": "Autohaus Schmid", "shop": "car", "website": "https://schmid.example"}},
    {"type": "node", "id": 4, "lat": 48.125, "lon": 7.855,
     "tags": {"name": "Sparkasse Filiale", "amenity": "bank"}},
    {"type": "node", "id": 5, "lat": 48.2, "lon": 7.9,
     "tags": {"name": "Gasthaus Adler", "amenity": "restaurant"}},
    {"type": "node", "id": 6, "lat": 48.122, "lon": 7.852, "tags": {"shop": "bakery"}},  # ohne Name
    {"type": "node", "id": 7, "lat": 48.123, "lon": 7.853,
     "tags": {"name": "Elektro Maurer", "craft": "electrician"}},
]


@pytest.fixture
def osm_gemockt(monkeypatch):
    monkeypatch.setattr(osm, "_roh_holen", lambda lat, lon, r: ELEMENTE)


def test_betriebe_branchen_duplikate_adresse(osm_gemockt):
    betriebe = osm.betriebe_im_umkreis(*VEREIN, radius_km=15)
    namen = [b.name for b in betriebe]
    assert namen.count("Bäckerei Müller") == 1
    baecker = next(b for b in betriebe if b.name == "Bäckerei Müller")
    assert baecker.branche == "Bäckereien"
    assert baecker.adresse == "Hauptstr. 3"
    assert baecker.website == "https://baeckerei-mueller.de"
    branchen = {b.name: b.branche for b in betriebe}
    assert branchen["Autohaus Schmid"] == "Autohäuser"
    assert branchen["Sparkasse Filiale"] == "Banken"
    assert branchen["Gasthaus Adler"] == "Gastronomie"
    assert branchen["Elektro Maurer"] == "Handwerk"
    assert betriebe == sorted(betriebe, key=lambda b: b.entfernung_km)


def test_vorfilter_schliesst_bestand_aus_und_erkennt_luecken(osm_gemockt):
    betriebe = osm.betriebe_im_umkreis(*VEREIN, radius_km=15)
    ergebnis = vorfilter.filtern(
        betriebe,
        freie_ids=["bande", "trikot_brust", "vereinsfest"],
        sponsoren_namen=["Sparkasse Freiburg", "Elektro Maurer GmbH"],
        radius_km=15,
    )
    namen = [k.betrieb.name for k in ergebnis.kandidaten]
    assert "Elektro Maurer" not in namen  # Bestandssponsor
    assert ergebnis.ausgeschlossen_bestand == 1
    luecken = {l["branche"] for l in ergebnis.luecken}
    assert "Banken" not in luecken  # Sparkasse ist schon Sponsor
    assert {"Bäckereien", "Autohäuser"} <= luecken
    baecker = next(k for k in ergebnis.kandidaten if k.betrieb.name == "Bäckerei Müller")
    assert set(baecker.passende_pakete) == {"bande", "vereinsfest"}
    assert 0 <= baecker.score <= 100
    assert any("Noch kein Sponsor" in g for g in baecker.gruende)


def test_vorfilter_ohne_website_und_weit_weg_niedriger():
    nah = Betrieb(osm_id="n/1", name="A", branche="Handwerk", osm_typ="craft=x",
                  lat=0, lon=0, website="https://a.example", entfernung_km=1)
    fern = nah.model_copy(update={"osm_id": "n/2", "name": "B", "website": None, "entfernung_km": 14})
    e = vorfilter.filtern([fern, nah], ["bande"], [], radius_km=15)
    assert [k.betrieb.name for k in e.kandidaten] == ["A", "B"]


def test_sponsor_branche_aus_namen():
    assert vorfilter.sponsor_branche("Volksbank Breisgau Nord") == "Banken"
    assert vorfilter.sponsor_branche("Autohaus Rees") == "Autohäuser"
    assert vorfilter.sponsor_branche("Joma") is None


def test_api_kandidaten_suchen_und_status(osm_gemockt, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def session_override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = session_override
    monkeypatch.setattr("app.services.geo.geokodieren", lambda ort: VEREIN)
    try:
        with TestClient(app) as c:
            vid = c.post("/vereine", json={"name": "FC Test", "ort": "Teststadt"}).json()["id"]
            c.post(f"/vereine/{vid}/sponsoren", json=[{"firma": "Elektro Maurer"}])
            antwort = c.post(f"/vereine/{vid}/kandidaten?anzahl=10")
            assert antwort.status_code == 200, antwort.text
            daten = antwort.json()
            assert daten["hinweise"]  # kein Inventar gepflegt
            assert len(daten["kandidaten"]) == 4
            kid = daten["kandidaten"][0]["id"]
            assert c.patch(f"/kandidaten/{kid}/status", json={"status": "kontaktiert"}).json()["status"] == "kontaktiert"
            assert c.patch(f"/kandidaten/{kid}/status", json={"status": "quatsch"}).status_code == 422
            # zweite Suche: bearbeiteter Kandidat bleibt, keine Duplikate
            zweite = c.post(f"/vereine/{vid}/kandidaten?anzahl=10").json()["kandidaten"]
            assert len(zweite) == 4
            assert any(k["status"] == "kontaktiert" for k in zweite)
    finally:
        app.dependency_overrides.clear()


def test_ketten_im_handel_raus_banken_bleiben():
    basis = dict(osm_typ="x", lat=0, lon=0, website="https://x.example", entfernung_km=1)
    tedi = Betrieb(osm_id="n/1", name="TEDi", branche="Handel", kette=True, **basis)
    spk = Betrieb(osm_id="n/2", name="Sparkasse", branche="Banken", kette=True, **basis)
    laden = Betrieb(osm_id="n/3", name="Modehaus Blum", branche="Handel", **basis)
    e = vorfilter.filtern([tedi, spk, laden], ["bande", "anzeigetafel"], [], radius_km=15)
    namen = [k.betrieb.name for k in e.kandidaten]
    assert "TEDi" not in namen
    assert namen[0] == "Sparkasse"  # Banken: höhere Sponsoring-Nähe als Handel
