"""Austauschbare Websuche. Erste Umsetzung: Exa.

Exa-Nutzung nach dem Skill `build-with-exa`:
- Bekannte URLs  -> /contents (Inhaltsfelder auf oberster Ebene, `statuses` prüfen)
- Freie Suche    -> /search mit `type="auto"`, `contents={"highlights": True}`
  und `objective`, weil jede Suche ein Schritt unserer Pipeline ist.
- Keine Deko-Parameter (kein numResults, category, Domain-Filter, Datumsfilter).
- Ruft ein Sprachmodell die Suche als Werkzeug auf, schreibt es query und
  objective selbst. objective-Beschreibung steht wortgetreu am Werkzeug.
"""

import logging
from types import SimpleNamespace
from typing import Any, Protocol

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Wortlaut der Exa-Doku für den objective-Parameter eines Suchwerkzeugs.
OBJECTIVE_BESCHREIBUNG = (
    "Goal for this search turn; say which documents should rank first, "
    "which should be excluded, and what specific facts or figures to pull from them."
)
WERKZEUG_NAME = "exa_search"
WERKZEUG_BESCHREIBUNG = (
    "Search the live web and return the most relevant URLs and content. "
    "Use for fresh information beyond the model's training data."
)
# Auf /contents gibt es keine Suchanfrage, an der Highlights hängen.
# Die Objektform trägt deshalb eine eigene Fokus-Anfrage.
UNTERNEHMEN_HIGHLIGHT_QUERY = (
    "Sponsoring, Vereinsförderung und lokales Engagement des Unternehmens"
)

from app.config import get_settings
from app.providers.cache import zwischengespeichert

# Unterseiten einer Vereinswebsite, die für Profil und Sponsoren zählen.
VEREIN_UNTERSEITEN = [
    "mannschaften",
    "teams",
    "sponsoren",
    "partner",
    "verein",
    "termine",
    "veranstaltungen",
]


class Fundstelle(BaseModel):
    """Ein Stück Webtext mit seiner Quelle. Grundlage für jede spätere Aussage."""

    url: str
    titel: str | None = None
    text: str
    datum: str | None = None


class WebsucheFehler(RuntimeError):
    pass


class Websuche(Protocol):
    def vereinsseite_lesen(self, url: str) -> list[Fundstelle]:
        """Startseite plus relevante Unterseiten eines Vereins als Volltext."""

    def unternehmensseite_lesen(self, url: str) -> list[Fundstelle]:
        """Website eines Kandidaten als kompakte Auszüge."""

    def engagement_suchen(self, firma: str, ort: str) -> list[Fundstelle]:
        """Webfunde zu Sponsoring und lokalem Engagement eines Unternehmens."""


def _ergebnisse_zu_fundstellen(ergebnisse: list, volltext: bool) -> list[dict]:
    fundstellen: list[dict] = []
    for r in ergebnisse:
        if volltext:
            text = r.text or ""
        else:
            text = "\n".join(r.highlights or [])
        if text.strip():
            fundstellen.append(
                {"url": r.url, "titel": r.title, "text": text, "datum": r.published_date}
            )
        for unterseite in getattr(r, "subpages", None) or []:
            fundstellen.extend(_ergebnisse_zu_fundstellen([unterseite], volltext))
    return fundstellen


def _status_text(status) -> str:
    fehler = getattr(status, "error", None)
    tag = getattr(fehler, "tag", None) if fehler is not None else None
    return f"{getattr(status, 'id', 'unbekannte URL')}: {tag or getattr(status, 'status', 'fehler')}"


def _statuses_pruefen(antwort, urls: list[str]) -> None:
    """/contents liefert HTTP 200 auch bei Teilfehlern; nur Komplettausfall ist ein Fehler."""
    statuses = getattr(antwort, "statuses", None) or []
    fehler = [s for s in statuses if s.status != "success"]
    for status in fehler:
        logger.error("Exa-Inhalt fehlgeschlagen: %s", _status_text(status))
    if statuses and len(fehler) == len(urls):
        details = ", ".join(_status_text(s) for s in fehler)
        raise WebsucheFehler(f"Seite nicht abrufbar ({details})")


def _hinweise_loggen(antwort) -> list[str]:
    """Notices gehören zum Modellergebnis, Warnungen nur ins Log."""
    hinweise: list[str] = []
    for hinweis in getattr(antwort, "notices", None) or []:
        text = getattr(hinweis, "message", None)
        if text:
            hinweise.append(text)
            logger.info("Exa-Hinweis: %s", text)
    for warnung in getattr(antwort, "warnings", None) or []:
        logger.warning(
            "Exa-Warnung %s bei %s: %s",
            getattr(warnung, "code", ""),
            getattr(warnung, "path", ""),
            getattr(warnung, "message", ""),
        )
    return hinweise


def _roh_zu_antwort(daten: dict) -> SimpleNamespace:
    """Antwort von POST /contents, ohne das SDK-Default `text` dazuzumischen."""
    ergebnisse = []
    for eintrag in daten.get("results") or []:
        unterseiten = [
            SimpleNamespace(
                url=unter.get("url"),
                title=unter.get("title"),
                text=unter.get("text"),
                highlights=unter.get("highlights") or [],
                published_date=unter.get("publishedDate"),
                subpages=[],
            )
            for unter in eintrag.get("subpages") or []
        ]
        ergebnisse.append(
            SimpleNamespace(
                url=eintrag.get("url"),
                title=eintrag.get("title"),
                text=eintrag.get("text"),
                highlights=eintrag.get("highlights") or [],
                published_date=eintrag.get("publishedDate"),
                subpages=unterseiten,
            )
        )
    statuses = []
    for status in daten.get("statuses") or []:
        fehler = status.get("error") if isinstance(status.get("error"), dict) else None
        statuses.append(
            SimpleNamespace(
                id=status.get("id"),
                status=status.get("status"),
                error=SimpleNamespace(tag=fehler.get("tag")) if fehler else None,
            )
        )
    return SimpleNamespace(
        results=ergebnisse,
        statuses=statuses,
        notices=daten.get("notices") or [],
        warnings=daten.get("warnings") or [],
    )


def exa_search_parameter() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "objective": {
                "type": "string",
                "description": OBJECTIVE_BESCHREIBUNG,
            },
        },
        "required": ["query", "objective"],
    }


def werkzeug_neutral() -> dict[str, Any]:
    return {
        "name": WERKZEUG_NAME,
        "description": WERKZEUG_BESCHREIBUNG,
        "parameters": exa_search_parameter(),
    }


def werkzeug_openai() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": WERKZEUG_NAME,
            "description": WERKZEUG_BESCHREIBUNG,
            "parameters": exa_search_parameter(),
        },
    }


def werkzeug_anthropic() -> dict[str, Any]:
    return {
        "name": WERKZEUG_NAME,
        "description": WERKZEUG_BESCHREIBUNG,
        "input_schema": exa_search_parameter(),
    }


def formatiere_fuer_modell(antwort) -> str:
    """Suchtext für das Sprachmodell. Warnungen bleiben draußen."""
    hinweise = _hinweise_loggen(antwort)
    bloecke: list[str] = []
    for eintrag in getattr(antwort, "results", None) or []:
        highlights = [str(teil) for teil in (getattr(eintrag, "highlights", None) or []) if teil]
        zeilen = [
            f"Title: {getattr(eintrag, 'title', None) or 'N/A'}",
            f"URL: {getattr(eintrag, 'url', None) or 'N/A'}",
            f"Published: {getattr(eintrag, 'published_date', None) or 'N/A'}",
            f"Author: {getattr(eintrag, 'author', None) or 'N/A'}",
        ]
        if highlights:
            zeilen.append("Highlights:\n" + "\n".join(highlights))
        elif getattr(eintrag, "text", None):
            zeilen.append(f"Text: {eintrag.text}")
        bloecke.append("\n".join(zeilen))
    text = "\n\n---\n\n".join(bloecke) or "No search results found."
    notizen = [f"Note: {hinweis}" for hinweis in hinweise]
    if not notizen:
        return text
    return "\n".join(notizen) + "\n\n" + text


class ExaWebsuche:
    def __init__(self, api_key: str) -> None:
        from exa_py import Exa

        if not api_key:
            raise WebsucheFehler("EXA_API_KEY fehlt in backend/.env")
        self._exa = Exa(api_key=api_key)

    def vereinsseite_lesen(self, url: str) -> list[Fundstelle]:
        def holen() -> list[dict]:
            # Volltext statt Highlights: Die Profil-Extraktion braucht den
            # breiten Seitenkontext (Mannschaften, Ligen, Sponsorenlogos).
            antwort = self._exa.get_contents(
                [url],
                text=True,
                subpages=8,
                subpage_target=VEREIN_UNTERSEITEN,
            )
            _statuses_pruefen(antwort, [url])
            return _ergebnisse_zu_fundstellen(antwort.results, volltext=True)

        roh = zwischengespeichert("exa-verein", holen, url=url)
        return [Fundstelle(**f) for f in roh]

    def unternehmensseite_lesen(self, url: str) -> list[Fundstelle]:
        def holen() -> list[dict]:
            # Nur Highlights. exa-py 2.28 hängt bei get_contents sonst
            # zusätzlich text mit 10.000 Zeichen an, sobald text fehlt.
            antwort = _roh_zu_antwort(
                self._exa.request(
                    "/contents",
                    {
                        "urls": [url],
                        "highlights": {"query": UNTERNEHMEN_HIGHLIGHT_QUERY},
                    },
                )
            )
            _statuses_pruefen(antwort, [url])
            _hinweise_loggen(antwort)
            return _ergebnisse_zu_fundstellen(antwort.results, volltext=False)

        roh = zwischengespeichert("exa-unternehmen", holen, url=url)
        return [Fundstelle(**f) for f in roh]

    def engagement_suchen(self, firma: str, ort: str) -> list[Fundstelle]:
        def holen() -> list[dict]:
            antwort = self._exa.search(
                f"Sponsoring, Vereinsförderung und lokales Engagement von {firma} in {ort}",
                type="auto",
                contents={"highlights": True},
                objective=(
                    f"Belege, ob das Unternehmen {firma} aus {ort} Vereine, Sport, "
                    "Jugendarbeit oder lokale Veranstaltungen unterstützt oder "
                    "gesponsert hat. Zuerst Seiten des Unternehmens selbst, von "
                    "Vereinen und aus der Lokalpresse; Branchenverzeichnisse und "
                    "Seiten über gleichnamige Firmen anderswo ausschließen. "
                    "Konkrete Vereine, Anlässe, Beträge und Jahre herausziehen."
                ),
                user_location="DE",
            )
            _hinweise_loggen(antwort)
            return _ergebnisse_zu_fundstellen(antwort.results, volltext=False)

    def fuehre_werkzeug_aus(self, query: str, objective: str) -> str:
        """exa_search: query und objective des Modells gehen unverändert an /search."""
        suchtext = (query or "").strip()
        ziel = (objective or "").strip()
        if not suchtext or not ziel:
            raise ValueError("query und objective sind Pflicht")

        def holen() -> str:
            antwort = self._exa.search(
                suchtext,
                objective=ziel,
                type="auto",
                contents={"highlights": True},
            )
            return formatiere_fuer_modell(antwort)

        return zwischengespeichert("exa-werkzeug", holen, query=suchtext, objective=ziel)

        roh = zwischengespeichert("exa-engagement", holen, firma=firma, ort=ort)
        return [Fundstelle(**f) for f in roh]


class NurCacheWebsuche(ExaWebsuche):
    """Für DEMO_MODE: kein Key nötig, alle Antworten kommen aus cache/demo/."""

    def __init__(self) -> None:  # noqa: D107 - bewusst ohne Exa-Client
        self._exa = None


def websuche() -> Websuche:
    settings = get_settings()
    if settings.demo_mode:
        return NurCacheWebsuche()
    return ExaWebsuche(settings.exa_api_key)
