"""Finanzierungsplan: Auswahl, Status und Kandidaten je Planzeile."""

from app.models import Kandidat, Unternehmen
from app.services.plan import planen
from app.services.potenzial import Paket, Potenzial


def _potenzial(pakete: list[Paket], bestand: int = 0) -> Potenzial:
    return Potenzial(
        spanne_min=sum(p.min for p in pakete), spanne_max=sum(p.max for p in pakete),
        freie_pakete=pakete, sachleistungen=[], vergebene_pakete=[], bestand_eur=bestand,
        bestand_sponsoren=1 if bestand else 0, luecken=[], betriebe_im_umkreis=None,
        annahmen=[], hinweis="",
    )


def _paket(kid: str, lo: int, hi: int, frei: int = 1) -> Paket:
    return Paket(katalog_id=kid, name=kid.title(), kategorie="k", min=lo * frei, max=hi * frei,
                 quelle="schaetzung", einheiten_frei=frei)


PAKETE = [
    _paket("trikot_brust", 2000, 3000),  # Mitte 2500
    _paket("bande", 400, 800, frei=4),  # je Bande Mitte 600
    _paket("website", 200, 400),  # Mitte 300
]


def test_ohne_ziel_und_ziel_erreicht():
    assert planen(_potenzial(PAKETE), None, []).status == "ohne_ziel"
    plan = planen(_potenzial(PAKETE, bestand=5000), 4000, [])
    assert plan.status == "erreicht" and plan.luecke_eur == -1000 and plan.zeilen == []


def test_hauptsponsor_dann_partner_bis_die_luecke_gedeckt_ist():
    # Lücke 6000 − 1000 = 5000: Trikot 2500 als Anker, dann 4 Banden à 600 = 4900, Website schließt.
    plan = planen(_potenzial(PAKETE, bestand=1000), 6000, [])
    zeilen = {z.katalog_id: z for z in plan.zeilen}
    assert plan.luecke_eur == 5000
    assert plan.zeilen[0].katalog_id == "trikot_brust"
    assert zeilen["bande"].anzahl == 4 and (zeilen["bande"].min, zeilen["bande"].max) == (1600, 3200)
    assert "website" in zeilen
    assert plan.neue_sponsoren == 6
    assert (plan.summe_min, plan.summe_max) == (3800, 6600)
    assert plan.status == "knapp"  # Mitte reicht, Untergrenze nicht
    assert plan.hebel


def test_kleine_luecke_schliesst_eine_passende_einheit():
    plan = planen(_potenzial(PAKETE), 550, [])
    assert [(z.katalog_id, z.anzahl) for z in plan.zeilen] == [("bande", 1)]
    assert plan.status == "knapp"  # Bande 400–800 deckt 550 nur in der Mitte

    plan = planen(_potenzial(PAKETE), 2000, [])
    assert [z.katalog_id for z in plan.zeilen] == ["trikot_brust"]
    assert plan.status == "erreichbar"  # schon die Untergrenze 2000 deckt das Ziel


def test_ziel_ueber_potenzial_nennt_fehlbetrag():
    plan = planen(_potenzial(PAKETE), 20000, [])
    assert plan.status == "ueber_potenzial"
    assert plan.neue_sponsoren == 6  # alles verplant
    assert "es fehlen etwa" in plan.hebel[0]


def test_kandidaten_geprueft_zuerst_verschiedene_firmen_ohne_absagen():
    def k(i: int, **kw) -> tuple[Kandidat, Unternehmen]:
        kw.setdefault("vorfilter_score", 50)
        kand = Kandidat(id=i, verein_id=1, unternehmen_id=i, entfernung_km=1, **kw)
        return kand, Unternehmen(id=i, osm_id=f"n/{i}", name=f"Firma {i}", branche="Handwerk", lat=0, lon=0)

    kandidaten = [
        k(1, recherche_status="fertig", score=60, paket_empfehlung={"katalog_ids": ["bande"]}),
        k(2, recherche_status="fertig", score=90, paket_empfehlung={"katalog_ids": ["bande"]}),
        k(3, recherche_status="offen", vorfilter_score=99, paket_empfehlung={"passende_pakete": ["bande"]}),
        k(4, recherche_status="fertig", score=95, status="absage", paket_empfehlung={"katalog_ids": ["bande"]}),
        k(5, recherche_status="fertig", score=70, paket_empfehlung={"katalog_ids": ["trikot_brust"]}),
    ]
    plan = planen(_potenzial(PAKETE), 5000, kandidaten)
    zeilen = {z.katalog_id: z for z in plan.zeilen}
    bande = zeilen["bande"].kandidaten
    assert [c.kandidat_id for c in bande] == [2, 1, 3]
    assert [c.geprueft for c in bande] == [True, True, False]
    assert [c.kandidat_id for c in zeilen["trikot_brust"].kandidaten] == [5]
