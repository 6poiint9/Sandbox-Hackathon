"""Austauschbare Websuche. Erste Umsetzung: Exa.

Exa-Nutzung nach dem Skill `build-with-exa` (.claude/skills/build-with-exa):
- Bekannte URLs  -> /contents (Inhaltsfelder auf oberster Ebene, `statuses` prüfen)
- Freie Suche    -> /search mit `type="auto"`, `contents={"highlights": True}`
  und `objective`, weil jede Suche ein Schritt unserer Pipeline ist.
- Keine Deko-Parameter (kein numResults, category, Domain-Filter, Datumsfilter).
"""

from typing import Protocol

from pydantic import BaseModel

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


def _statuses_pruefen(antwort, urls: list[str]) -> None:
    """/contents liefert HTTP 200 auch bei Teilfehlern; nur Komplettausfall ist ein Fehler."""
    statuses = getattr(antwort, "statuses", None) or []
    fehler = [s for s in statuses if s.status != "success"]
    if statuses and len(fehler) == len(urls):
        details = ", ".join(f"{s.id}: {getattr(s.error, 'tag', s.status)}" for s in fehler)
        raise WebsucheFehler(f"Seite nicht abrufbar ({details})")


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
            antwort = self._exa.get_contents([url], highlights=True)
            _statuses_pruefen(antwort, [url])
            return _ergebnisse_zu_fundstellen(antwort.results, volltext=False)

        roh = zwischengespeichert("exa-unternehmen", holen, url=url)
        return [Fundstelle(**f) for f in roh]

    def engagement_suchen(self, firma: str, ort: str) -> list[Fundstelle]:
        def holen() -> list[dict]:
            antwort = self._exa.search(
                f"{firma} {ort} Sponsoring Verein Engagement",
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
            return _ergebnisse_zu_fundstellen(antwort.results, volltext=False)

        roh = zwischengespeichert("exa-engagement", holen, firma=firma, ort=ort)
        return [Fundstelle(**f) for f in roh]

    def strukturiert_suchen(
        self,
        query: str,
        objective: str,
        system_prompt: str,
        schema: dict,
        domain: str | None = None,
    ) -> "StrukturierteAntwort":
        """Felder aus Webseiten ziehen (Exa outputSchema), je Feld mit Quellen.

        `domain` beschränkt hart auf eine vom Nutzer angegebene Website
        (die eigene Vereinsseite) – das ist die einzige erlaubte Domain-Liste.
        """

        def holen() -> dict:
            optionen: dict = {
                "type": "auto",
                "contents": {"highlights": True},
                "objective": objective,
                "system_prompt": system_prompt,
                "output_schema": schema,
            }
            if domain:
                optionen["include_domains"] = [domain]
            antwort = self._exa.search(query, **optionen)
            ausgabe = antwort.output
            inhalt = ausgabe.content if ausgabe and isinstance(ausgabe.content, dict) else {}
            belege = [
                {
                    "feld": g.field,
                    "urls": [c.url for c in g.citations],
                    "sicherheit": g.confidence,
                }
                for g in (ausgabe.grounding if ausgabe else [])
            ]
            return {
                "inhalt": inhalt,
                "belege": belege,
                "fundstellen": _ergebnisse_zu_fundstellen(antwort.results, volltext=False),
            }

        roh = zwischengespeichert(
            "exa-strukturiert", holen, query=query, schema=schema, domain=domain
        )
        return StrukturierteAntwort(**roh)


class Beleg(BaseModel):
    feld: str
    urls: list[str]
    sicherheit: str


class StrukturierteAntwort(BaseModel):
    inhalt: dict
    belege: list[Beleg]
    fundstellen: list[Fundstelle]


class NurCacheWebsuche(ExaWebsuche):
    """Für DEMO_MODE: kein Key nötig, alle Antworten kommen aus cache/demo/."""

    def __init__(self) -> None:  # noqa: D107 - bewusst ohne Exa-Client
        self._exa = None


def websuche() -> Websuche:
    settings = get_settings()
    if settings.demo_mode:
        return NurCacheWebsuche()
    return ExaWebsuche(settings.exa_api_key)
