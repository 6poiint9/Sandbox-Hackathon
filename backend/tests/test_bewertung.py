"""Phase 4: Bewertung prüft Quellen, Pakete und Preise; Recherche fängt Fehler ab."""

from sqlmodel import Session, SQLModel, create_engine

from app.models import Kandidat, Unternehmen, Verein
from app.providers.websuche import Fundstelle, WebsucheFehler
from app.services import bewertung, potenzial, recherche
from app.services.bewertung import Grund, ModellBewertung

VEREIN = Verein(id=1, konto_id=1, name="FC Test", ort="Emmendingen", spielklasse="Landesliga", zuschauer_schnitt=150)
U = Unternehmen(id=1, osm_id="n/1", name="Bäckerei Müller", branche="Bäckereien", lat=0, lon=0,
                website="https://mueller.example")
K = Kandidat(id=1, verein_id=1, unternehmen_id=1, entfernung_km=1.2, vorfilter_score=80,
             paket_empfehlung={"passende_pakete": ["bande", "vereinsfest"]})


class FakeSuche:
    def __init__(self, kaputt=False):
        self.kaputt = kaputt

    def unternehmensseite_lesen(self, url):
        if self.kaputt:
            raise WebsucheFehler("CRAWL_NOT_FOUND")
        return [Fundstelle(url=url, text="Familienbäckerei seit 1950 in Emmendingen")]

    def engagement_suchen(self, firma, ort):
        return [
            Fundstelle(url="https://zeitung.example/a", text="Bäckerei Müller spendet für Jugendturnier"),
            Fundstelle(url=U.website, text="doppelt"),  # Duplikat wird entfernt
        ]


class FakeModell:
    name = "fake"

    def __init__(self, antwort):
        self.antwort = antwort
        self.prompts = []

    def json(self, system, prompt, schema):
        self.prompts.append(prompt)
        return self.antwort


def antwort(**ueber):
    basis = dict(
        score=82,
        sicherheit="hoch",
        zusammenfassung="Familienbäckerei in Emmendingen.",
        gruende=[
            Grund(text="Unterstützt bereits ein Jugendturnier", quelle_nr=2),
            Grund(text="Traditionsbetrieb vor Ort", quelle_nr=1),
            Grund(text="Erfundene Quelle", quelle_nr=9),
        ],
        pakete=["vereinsfest", "trikot_brust"],  # trikot_brust ist NICHT frei
        paket_begruendung="Stand beim Fest passt zu Backwaren.",
    )
    basis.update(ueber)
    return ModellBewertung(**basis)


def test_bewertung_prueft_quellen_pakete_preise():
    modell = FakeModell(antwort())
    felder = bewertung.bewerten(modell, FakeSuche(), VEREIN, K, U, ["bande", "vereinsfest"])
    assert "[1]" in modell.prompts[0] and "[2]" in modell.prompts[0] and "[3]" not in modell.prompts[0]
    assert [g["quelle_url"] for g in felder["gruende"]] == ["https://zeitung.example/a", U.website]
    assert felder["sicherheit"] == "niedrig"  # nur 2 belegte Gründe
    assert felder["paket_empfehlung"]["katalog_ids"] == ["vereinsfest"]
    # vereinsfest 200–1000 € × 1,3 = 250–1300, mittleres Band 25–75 %
    assert felder["paket_empfehlung"]["preis_eur"] == {"min": 500, "max": 1050}


def test_website_fehler_wird_vermerkt_nicht_geworfen():
    felder = bewertung.bewerten(FakeModell(antwort()), FakeSuche(kaputt=True), VEREIN, K, U, ["bande"])
    assert "CRAWL_NOT_FOUND" in felder["recherche_fehler"]
    assert felder["paket_empfehlung"]["katalog_ids"] == ["bande"]  # Fallback auf Vorfilter-Paket


def test_richtpreis_faktoren():
    assert potenzial.spielklasse_faktor("Kreisliga A") == 0.8
    assert potenzial.spielklasse_faktor("Landesliga Südbaden") == 1.3
    assert potenzial.spielklasse_faktor(None) == 0.8
    kreis = Verein(name="x", ort="y", spielklasse="Kreisliga B", zuschauer_schnitt=30)
    assert potenzial.richtpreis("bande", kreis) == {"min": 200, "max": 950, "einheit": "saison", "quelle": "findasponsor"}
    assert potenzial.richtpreis("sachsponsoring", kreis) is None


def test_recherche_faengt_fehler_pro_kandidat_ab(monkeypatch, tmp_path):
    # Datei-DB wie im Betrieb: jeder Thread bekommt eine eigene Verbindung.
    eng = create_engine(f"sqlite:///{tmp_path / 't.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(Verein(id=1, konto_id=1, name="FC", ort="Ort"))
        s.add(Unternehmen(id=1, osm_id="n/1", name="Gut", branche="Handwerk", lat=0, lon=0))
        s.add(Unternehmen(id=2, osm_id="n/2", name="Kaputt", branche="Handwerk", lat=0, lon=0))
        s.add(Kandidat(id=1, verein_id=1, unternehmen_id=1, entfernung_km=1, vorfilter_score=50))
        s.add(Kandidat(id=2, verein_id=1, unternehmen_id=2, entfernung_km=1, vorfilter_score=50))
        s.commit()

    def fake_bewerten(modell, suche, verein, k, u, freie):
        if u.name == "Kaputt":
            raise RuntimeError("Quota erschöpft")
        return {"score": 70, "sicherheit": "mittel", "gruende": []}

    monkeypatch.setattr(recherche, "bewerten", fake_bewerten)
    monkeypatch.setattr(recherche, "analyse_modell", lambda: None)
    monkeypatch.setattr(recherche, "websuche", lambda: None)
    recherche.alle_recherchieren([1, 2], ["bande"], eng)

    with Session(eng) as s:
        gut, kaputt = s.get(Kandidat, 1), s.get(Kandidat, 2)
        assert (gut.recherche_status, gut.score) == ("fertig", 70)
        assert kaputt.recherche_status == "fehler" and "Quota" in kaputt.recherche_fehler
