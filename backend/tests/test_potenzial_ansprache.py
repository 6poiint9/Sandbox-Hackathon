"""Phase 5: Potenzialzahl, Ansprache (Modell gemockt) und CSV-Export."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import InventarPosten, Kandidat, Sponsor, Unternehmen, Verein
from app.services import ansprache as ansprache_service
from app.services.ansprache import AnspracheText
from app.services.potenzial import berechnen


def test_potenzial_rechnet_nur_freie_pakete_mittleres_band():
    v = Verein(id=1, name="FC", ort="O", spielklasse="Bezirksliga", zuschauer_schnitt=100,
               mannschaften=[{"name": "1. Herren"}, {"name": "D-Jugend"}, {"name": "E-Junioren"}],
               luecken=[{"branche": "Autohäuser", "betriebe": 12}])
    inventar = [
        InventarPosten(verein_id=1, katalog_id="bande"),  # 300–1500, Faktor 1,0
        InventarPosten(verein_id=1, katalog_id="trikot_jugend"),  # 400–1200 je Satz × 2 Jugendteams
        InventarPosten(verein_id=1, katalog_id="trikot_brust", verfuegbar=False),
        InventarPosten(verein_id=1, katalog_id="sachsponsoring"),
        InventarPosten(verein_id=1, katalog_id="website", preis_eur=250),  # eigener Preis
    ]
    p = berechnen(v, inventar, [Sponsor(id=1, verein_id=1, firma="X", betrag_eur=3000)])
    pakete = {x.katalog_id: x for x in p.freie_pakete}
    assert (pakete["bande"].min, pakete["bande"].max) == (600, 1200)
    assert (pakete["trikot_jugend"].min, pakete["trikot_jugend"].max) == (1200, 2000)
    assert pakete["trikot_jugend"].menge == 2
    assert pakete["website"].eigener_preis and pakete["website"].min == 250
    assert "trikot_brust" not in pakete
    assert p.sachleistungen == ["Sach- oder Dienstleistungssponsoring"]
    assert (p.spanne_min, p.spanne_max) == (600 + 1200 + 250, 1200 + 2000 + 250)
    assert p.bestand_eur == 3000
    assert p.luecken[0]["branche"] == "Autohäuser"
    assert any("Jugendmannschaft" in a for a in p.annahmen)


class FakeModell:
    name = "fake"

    def __init__(self):
        self.prompt = None

    def json(self, system, prompt, schema):
        self.prompt = prompt
        return AnspracheText(brief="Sehr geehrte Damen und Herren, ...", leitfaden="- Begrüßung",
                             email_betreff="Wie besprochen", email_text="Hallo ...")


@pytest.fixture
def client(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(Verein(id=1, name="FC Test 03", ort="Emmendingen"))
        s.add(Unternehmen(id=1, osm_id="n/1", name="Bäckerei Müller", branche="Bäckereien", lat=0, lon=0))
        s.add(Unternehmen(id=2, osm_id="n/2", name="Offen GmbH", branche="Handel", lat=0, lon=0))
        s.add(Kandidat(id=1, verein_id=1, unternehmen_id=1, entfernung_km=1.25, vorfilter_score=80, score=82,
                       sicherheit="hoch", recherche_status="fertig",
                       gruende=[{"text": "Sponsert Jugendturnier", "quelle_url": "https://z.example/a"}],
                       paket_empfehlung={"namen": ["Bandenwerbung"], "preis_eur": {"min": 400, "max": 1300}}))
        s.add(Kandidat(id=2, verein_id=1, unternehmen_id=2, entfernung_km=3, vorfilter_score=50))
        s.commit()

    def override():
        with Session(eng) as s:
            yield s

    modell = FakeModell()
    app.dependency_overrides[get_session] = override
    monkeypatch.setattr("app.routers.analyse.text_modell", lambda: modell)
    with TestClient(app) as c:
        c.modell = modell
        yield c
    app.dependency_overrides.clear()


def test_ansprache_erzeugen_speichern_wiederverwenden(client):
    assert client.get("/kandidaten/1/ansprache").status_code == 404
    a = client.post("/kandidaten/1/ansprache").json()
    assert a["brief"].startswith("Sehr geehrte")
    assert "Sponsert Jugendturnier" in client.modell.prompt
    assert "400–1300 €" in client.modell.prompt
    client.modell.prompt = None
    assert client.post("/kandidaten/1/ansprache").json()["id"] == a["id"]
    assert client.modell.prompt is None  # gespeicherte Ansprache, kein neuer Modellaufruf
    assert client.post("/kandidaten/2/ansprache").status_code == 409  # nicht recherchiert


def test_export_csv(client):
    r = client.get("/vereine/1/export")
    assert r.status_code == 200
    assert "sponsorenkompass_FC_Test_03.csv" in r.headers["content-disposition"]
    zeilen = r.text.lstrip("﻿").splitlines()
    assert zeilen[0].startswith("Unternehmen;Branche")
    assert zeilen[1].startswith("Bäckerei Müller;Bäckereien")
    assert "1,2" in zeilen[1] and "https://z.example/a" in zeilen[1]
    assert len(zeilen) == 3


def test_prompt_ohne_gruende_bleibt_ehrlich():
    v = Verein(name="FC", ort="O")
    k = Kandidat(verein_id=1, unternehmen_id=1, entfernung_km=1, vorfilter_score=1)
    u = Unternehmen(osm_id="n", name="U", branche="Handel", lat=0, lon=0)
    assert "(keine belegten Gründe)" in ansprache_service.prompt_bauen(v, k, u)


def test_verhandlungsrahmen_einstieg_schmerzgrenze_und_guenstigeres_ausweichpaket():
    from app.services.ansprache import prompt_bauen, verhandlungsrahmen

    v = Verein(id=1, name="FC", ort="O", spielklasse="Bezirksliga", zuschauer_schnitt=100)
    k = Kandidat(id=1, verein_id=1, unternehmen_id=1, entfernung_km=1.0, vorfilter_score=50,
                 paket_empfehlung={"katalog_ids": ["trikot_brust"], "namen": ["Trikotbrust"],
                                   "preis_eur": {"min": 2000, "max": 3500},
                                   "passende_pakete": ["trikot_brust", "bande"]})
    rahmen = verhandlungsrahmen(v, k)
    assert (rahmen.einstieg_eur, rahmen.schmerzgrenze_eur) == (3500, 2000)
    assert rahmen.ausweich_paket == "Bandenwerbung"
    assert (rahmen.ausweich_min, rahmen.ausweich_max) == (600, 1200)

    u = Unternehmen(id=1, osm_id="n/1", name="Autohaus", branche="Autohäuser", lat=0, lon=0)
    prompt = prompt_bauen(v, k, u)
    assert "Einstiegspreis: 3500 €" in prompt and "Schmerzgrenze: 2000 €" in prompt
    assert "Sachsponsoring" in prompt

    k.paket_empfehlung = {}
    assert verhandlungsrahmen(v, k) is None
