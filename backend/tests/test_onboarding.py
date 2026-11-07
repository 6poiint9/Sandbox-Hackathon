"""Phase 2: CSV-Import, Zuordnung, Onboarding-Analyse und API-Ablauf."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.providers.websuche import Beleg, StrukturierteAntwort
from app.services import onboarding
from app.services.csv_import import betrag, importieren
from app.services.zuordnung import katalog_id

# --- Zuordnung und CSV ------------------------------------------------------


@pytest.mark.parametrize(
    "text,erwartet",
    [
        ("Bandenwerbung Hauptplatz", "bande"),
        ("Trikotsponsor 1. Mannschaft (Brust)", "trikot_brust"),
        ("Jugendtrikots D-Jugend", "trikot_jugend"),
        ("trikot_brust", "trikot_brust"),
        ("Ausrichter Sparkassen-Cup", "turnier"),
        ("irgendwas völlig anderes", None),
    ],
)
def test_katalog_zuordnung(text, erwartet):
    assert katalog_id(text) == erwartet


def test_betrag_deutsch_und_englisch():
    assert betrag("1.500,00 €") == 1500
    assert betrag("1.500") == 1500
    assert betrag("600") == 600
    assert betrag("") is None


def test_csv_vorlage_semikolon():
    with open("../docs/vorlage-bestandssponsoren.csv", "rb") as f:
        ergebnis = importieren(f.read())
    assert ergebnis.fehler == []
    assert [s.firma for s in ergebnis.sponsoren] == ["Beispiel Bäckerei GmbH", "Beispiel Autohaus KG"]
    assert ergebnis.sponsoren[0].gegenleistung == "bande"
    assert ergebnis.sponsoren[1].betrag_eur == 3000
    assert ergebnis.sponsoren[1].laufzeit_bis == date(2027, 6, 30)


def test_csv_komma_varianten_und_fehlerzeilen():
    csv = (
        "Unternehmen,Paket,Betrag,Vertragsende\n"
        "Metzgerei Huber,Bandenwerbung,\"1.200,00 €\",30.06.2027\n"
        ",Trikot,500,\n"
        "Optik Klar,Jugendtrikots,400,irgendwann\n"
    ).encode()
    ergebnis = importieren(csv)
    assert [s.firma for s in ergebnis.sponsoren] == ["Metzgerei Huber"]
    assert ergebnis.sponsoren[0].betrag_eur == 1200
    assert len(ergebnis.fehler) == 2


def test_csv_ohne_firmenspalte():
    assert importieren(b"a;b\n1;2\n").fehler == ["Spalte 'firma' fehlt in der Kopfzeile."]


# --- Onboarding-Analyse -----------------------------------------------------


class FakeSuche:
    def __init__(self):
        self.anfragen = []

    def strukturiert_suchen(self, query, objective, system_prompt, schema, domain=None):
        self.anfragen.append({"query": query, "domain": domain, "schema": schema})
        if "sponsoren" in schema["properties"]:
            inhalt = {
                "sponsoren": [
                    {"firma": "Sparkasse", "gegenleistung": "Trikot Brust 1. Mannschaft"},
                    {"firma": "Bäckerei Müller", "gegenleistung": "Bande"},
                    {"firma": ""},
                ]
            }
        else:
            inhalt = {
                "name": "FC Beispiel",
                "sportarten": ["Fußball"],
                "mannschaften": [
                    {"name": "D-Jugend", "spielklasse": "Kreisstaffel"},
                    {"name": "1. Herren", "spielklasse": "Kreisliga A"},
                ],
                "veranstaltungen": ["Sommerturnier"],
            }
        beleg = Beleg(feld="name", urls=["https://fc.example"], sicherheit="high")
        return StrukturierteAntwort(inhalt=inhalt, belege=[beleg], fundstellen=[])


def test_analyse_baut_profilvorschlag():
    suche = FakeSuche()
    v = onboarding.analysieren(suche, "https://www.fc-beispiel.de/", "Emmendingen")
    assert {a["domain"] for a in suche.anfragen} == {"fc-beispiel.de"}
    assert v.name == "FC Beispiel"
    assert v.spielklasse == "Kreisliga A"
    assert v.mitglieder is None  # nicht gefunden -> leer, nicht geschätzt
    assert [s.firma for s in v.sponsoren] == ["Sparkasse", "Bäckerei Müller"]
    assert v.inventar_vergeben == ["bande", "trikot_brust"]
    assert v.belege[0].urls == ["https://fc.example"]


# --- API-Ablauf -------------------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def session_override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = session_override
    monkeypatch.setattr("app.routers.onboarding.websuche", lambda: FakeSuche())
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_api_onboarding_ablauf(client):
    vorschlag = client.post(
        "/onboarding/analyse", json={"website": "fc-beispiel.de", "ort": "Emmendingen"}
    ).json()
    assert vorschlag["name"] == "FC Beispiel"

    verein = client.post(
        "/vereine",
        json={
            "name": vorschlag["name"],
            "ort": "Emmendingen",
            "website": vorschlag["website"],
            "sportarten": vorschlag["sportarten"],
            "mannschaften": vorschlag["mannschaften"],
            "spielklasse": vorschlag["spielklasse"],
            "zuschauer_schnitt": 120,
        },
    ).json()
    vid = verein["id"]
    assert client.patch(f"/vereine/{vid}", json={"mitglieder": 350}).json()["mitglieder"] == 350

    inventar = client.put(
        f"/vereine/{vid}/inventar",
        json=[{"katalog_id": "bande"}, {"katalog_id": "trikot_brust", "verfuegbar": False}],
    )
    assert inventar.status_code == 200 and len(inventar.json()) == 2
    assert client.put(f"/vereine/{vid}/inventar", json=[{"katalog_id": "gibtsnicht"}]).status_code == 422

    with open("../docs/vorlage-bestandssponsoren.csv", "rb") as f:
        imp = client.post(f"/vereine/{vid}/sponsoren/import", files={"datei": ("s.csv", f, "text/csv")})
    assert imp.status_code == 200
    assert len(imp.json()["importiert"]) == 2
    assert len(client.get(f"/vereine/{vid}/sponsoren").json()) == 2
