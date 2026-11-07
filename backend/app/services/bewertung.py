"""Recherche und Bewertung eines Kandidaten.

1. Quellen sammeln: eigene Website (Exa /contents) + Engagement-Suche (Exa /search).
2. Sprachmodell bewertet NUR anhand der nummerierten Quellen:
   Score, Sicherheit, genau 3 Gründe mit Quellennummer, 1–2 Pakete aus den freien.
3. Code prüft: Quellennummern gültig, Pakete wirklich frei, Preis aus dem Katalog.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.data import katalog
from app.models import Kandidat, Unternehmen, Verein
from app.providers.llm import Sprachmodell
from app.providers.websuche import Fundstelle, Websuche, WebsucheFehler
from app.services.potenzial import richtpreis

MAX_QUELLEN = 10
MAX_ZEICHEN_JE_QUELLE = 1500

SYSTEM = """Du bewertest für einen Sportverein, wie gut ein lokales Unternehmen als Sponsor passt.
Regeln:
- Verwende ausschließlich Informationen aus den nummerierten Quellen. Nichts erfinden, nichts aus Vorwissen.
- Jeder Grund nennt die Nummer der Quelle, aus der er stammt.
- Achte darauf, dass eine Quelle wirklich DIESES Unternehmen betrifft (Name, Ort). Gleichnamige Firmen anderswo ignorieren.
- Wenig oder nichts gefunden: niedriger Score, sicherheit "niedrig", ehrliche Gründe (z. B. "keine Hinweise auf bisheriges Sponsoring").
- Pakete nur aus der Liste der freien Pakete wählen, passend zu Branche und Zielgruppe des Unternehmens.
- Schreibe sachlich auf Deutsch, kurze Sätze."""


class Grund(BaseModel):
    text: str = Field(description="Ein Satz, warum das Unternehmen passt oder nicht")
    quelle_nr: int = Field(description="Nummer der Quelle, z. B. 2")


class ModellBewertung(BaseModel):
    score: int = Field(ge=0, le=100)
    sicherheit: Literal["niedrig", "mittel", "hoch"]
    zusammenfassung: str = Field(description="Ein bis zwei Sätze Steckbrief des Unternehmens")
    gruende: list[Grund] = Field(min_length=1, max_length=3)
    pakete: list[str] = Field(description="1 bis 2 Katalog-IDs aus den freien Paketen")
    paket_begruendung: str


def quellen_sammeln(suche: Websuche, u: Unternehmen, ort: str) -> tuple[list[Fundstelle], list[str]]:
    funde: list[Fundstelle] = []
    fehler: list[str] = []
    if u.website:
        try:
            funde.extend(suche.unternehmensseite_lesen(u.website))
        except WebsucheFehler as e:
            fehler.append(f"Website: {e}")
    try:
        funde.extend(suche.engagement_suchen(u.name, ort))
    except WebsucheFehler as e:
        fehler.append(f"Suche: {e}")
    eindeutig: dict[str, Fundstelle] = {}
    for f in funde:
        eindeutig.setdefault(f.url, f)
    return list(eindeutig.values())[:MAX_QUELLEN], fehler


def prompt_bauen(verein: Verein, u: Unternehmen, entfernung: float, freie: list[str], quellen: list[Fundstelle]) -> str:
    kat = katalog.nach_id()
    mannschaften = ", ".join(
        f"{m.get('name')} ({m.get('spielklasse')})" for m in verein.mannschaften[:6] if m.get("name")
    )
    pakete = "\n".join(f"- {k}: {kat[k]['name']} – {kat[k]['gegenleistung']}" for k in freie)
    q = "\n\n".join(
        f"[{i}] {f.titel or ''} ({f.url})\n{f.text[:MAX_ZEICHEN_JE_QUELLE]}" for i, f in enumerate(quellen, 1)
    ) or "(keine Quellen gefunden)"
    return f"""VEREIN
Name: {verein.name} | Ort: {verein.ort} | Sportarten: {", ".join(verein.sportarten) or "-"}
Mannschaften: {mannschaften or "-"}
Veranstaltungen: {", ".join(verein.veranstaltungen) or "-"}
Mitglieder: {verein.mitglieder or "unbekannt"} | Zuschauer je Heimspiel: {verein.zuschauer_schnitt or "unbekannt"}

UNTERNEHMEN
Name: {u.name} | Branche: {u.branche} | Adresse: {u.adresse or "-"} | Entfernung: {entfernung:.1f} km
Website: {u.website or "-"}

FREIE PAKETE DES VEREINS
{pakete}

QUELLEN
{q}

Bewerte die Passung als Sponsor (0–100) mit genau drei Gründen."""


def bewerten(
    modell: Sprachmodell,
    suche: Websuche,
    verein: Verein,
    kandidat: Kandidat,
    u: Unternehmen,
    freie: list[str],
) -> dict:
    """Gibt die Felder zurück, die am Kandidaten gesetzt werden."""
    quellen, fehler = quellen_sammeln(suche, u, verein.ort)
    erg = modell.json(SYSTEM, prompt_bauen(verein, u, kandidat.entfernung_km, freie, quellen), ModellBewertung)

    gruende = []
    for g in erg.gruende[:3]:
        if 1 <= g.quelle_nr <= len(quellen):
            gruende.append({"text": g.text, "quelle_url": quellen[g.quelle_nr - 1].url})
    sicherheit = erg.sicherheit
    if len(gruende) < 3 or not quellen:
        sicherheit = "niedrig"

    pakete = [p for p in erg.pakete if p in freie][:2]
    if not pakete:
        pakete = (kandidat.paket_empfehlung or {}).get("passende_pakete", [])[:1]
    preise = [richtpreis(p, verein) for p in pakete]
    preis = None
    if any(preise):
        preis = {
            "min": sum(p["min"] for p in preise if p),
            "max": sum(p["max"] for p in preise if p),
        }

    return {
        "score": erg.score,
        "sicherheit": sicherheit,
        "zusammenfassung": erg.zusammenfassung,
        "gruende": gruende,
        "quellen": [{"url": f.url, "titel": f.titel} for f in quellen],
        "paket_empfehlung": {
            "katalog_ids": pakete,
            "namen": [katalog.nach_id()[p]["name"] for p in pakete],
            "preis_eur": preis,
            "begruendung": erg.paket_begruendung,
            "passende_pakete": (kandidat.paket_empfehlung or {}).get("passende_pakete", []),
        },
        "recherche_fehler": "; ".join(fehler) or None,
    }
