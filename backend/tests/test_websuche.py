"""Exa-Provider: externe Aufrufe sind gemockt."""

from types import SimpleNamespace

import pytest

from app.providers import websuche as ws
from app.providers.cache import DemoDatenFehlen


def ergebnis(url, text=None, highlights=None, subpages=None):
    return SimpleNamespace(
        url=url,
        title="Titel",
        text=text,
        highlights=highlights,
        published_date=None,
        subpages=subpages,
    )


class FakeExa:
    def __init__(self):
        self.aufrufe = []

    def get_contents(self, urls, **kwargs):
        self.aufrufe.append(("contents", urls, kwargs))
        unter = [ergebnis(urls[0] + "/sponsoren", text="Bäckerei Müller")]
        return SimpleNamespace(
            results=[ergebnis(urls[0], text="FC Beispiel, Kreisliga A", subpages=unter)],
            statuses=[SimpleNamespace(id=urls[0], status="success", error=None)],
        )

    def search(self, query, **kwargs):
        self.aufrufe.append(("search", query, kwargs))
        return SimpleNamespace(
            results=[ergebnis("https://zeitung.example/artikel", highlights=["spendet Trikots"])]
        )


@pytest.fixture
def suche():
    s = ws.ExaWebsuche("test-key")
    s._exa = FakeExa()
    return s


def test_vereinsseite_mit_unterseiten_und_volltext(suche):
    funde = suche.vereinsseite_lesen("https://fc.example")
    assert [f.url for f in funde] == ["https://fc.example", "https://fc.example/sponsoren"]
    _, _, kwargs = suche._exa.aufrufe[0]
    assert kwargs["text"] is True
    assert kwargs["subpages"] > 0
    assert "contents" not in kwargs  # /contents: Inhaltsfelder auf oberster Ebene


def test_engagement_suche_empfohlene_anfrage(suche):
    funde = suche.engagement_suchen("Bäckerei Müller", "Emmendingen")
    assert funde[0].text == "spendet Trikots"
    _, query, kwargs = suche._exa.aufrufe[0]
    assert "Bäckerei Müller" in query
    assert kwargs["contents"] == {"highlights": True}
    assert kwargs["type"] == "auto"
    assert kwargs["objective"]
    for deko in ("num_results", "category", "include_domains", "start_published_date"):
        assert deko not in kwargs


def test_ergebnis_wird_gecacht(suche):
    suche.engagement_suchen("Firma", "Ort")
    suche.engagement_suchen("Firma", "Ort")
    assert len(suche._exa.aufrufe) == 1


def test_komplettausfall_der_seite_ist_fehler(suche):
    def kaputt(urls, **kwargs):
        return SimpleNamespace(
            results=[],
            statuses=[SimpleNamespace(id=urls[0], status="error", error=SimpleNamespace(tag="CRAWL_NOT_FOUND"))],
        )

    suche._exa.get_contents = kaputt
    with pytest.raises(ws.WebsucheFehler, match="CRAWL_NOT_FOUND"):
        suche.unternehmensseite_lesen("https://weg.example")


def test_demo_mode_ohne_daten_ruft_nichts_extern(isolierter_cache, monkeypatch):
    monkeypatch.setattr(isolierter_cache, "demo_mode", True)
    suche = ws.websuche()
    assert isinstance(suche, ws.NurCacheWebsuche)
    with pytest.raises(DemoDatenFehlen):
        suche.engagement_suchen("Firma", "Ort")
