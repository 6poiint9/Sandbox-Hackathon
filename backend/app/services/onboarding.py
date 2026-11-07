"""Onboarding: Vereinswebsite auslesen und einen Profilvorschlag bauen.

Exa zieht die Felder direkt aus den Seiten (outputSchema) und liefert je Feld
Quellen und Sicherheit. Der Vorstand bestätigt oder korrigiert danach.
"""

from urllib.parse import urlparse

from pydantic import BaseModel

from app.providers.websuche import Beleg, Websuche
from app.services.zuordnung import katalog_id

NICHTS_ERFINDEN = (
    "Nutze ausschließlich Angaben, die auf den Seiten des Vereins stehen. "
    "Was nicht eindeutig belegt ist, bleibt leer (null oder leere Liste); niemals schätzen."
)

PROFIL_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "sportarten": {"type": "array", "items": {"type": "string"}},
        "mannschaften": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "spielklasse": {"type": "string"}},
            },
        },
        "mitglieder": {"type": "integer"},
        "veranstaltungen": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "sportarten", "mannschaften"],
}

SPONSOREN_SCHEMA = {
    "type": "object",
    "properties": {
        "sponsoren": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "firma": {"type": "string"},
                    "gegenleistung": {"type": "string"},
                    "website": {"type": "string"},
                },
                "required": ["firma"],
            },
        }
    },
    "required": ["sponsoren"],
}


class Mannschaft(BaseModel):
    name: str
    spielklasse: str | None = None


class ErkannterSponsor(BaseModel):
    firma: str
    gegenleistung_text: str | None = None
    gegenleistung: str | None = None  # katalog_id
    website: str | None = None


class ProfilVorschlag(BaseModel):
    name: str | None = None
    website: str
    ort: str
    sportarten: list[str] = []
    mannschaften: list[Mannschaft] = []
    spielklasse: str | None = None
    mitglieder: int | None = None
    veranstaltungen: list[str] = []
    sponsoren: list[ErkannterSponsor] = []
    inventar_vergeben: list[str] = []  # katalog_ids, die laut Website schon belegt sind
    belege: list[Beleg] = []
    hinweise: list[str] = []


def domain_von(website: str) -> str:
    url = website if "://" in website else f"https://{website}"
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def hoechste_spielklasse(mannschaften: list[Mannschaft]) -> str | None:
    """Spielklasse der ersten Herren-/Damenmannschaft, sonst der ersten mit Liga."""
    mit_liga = [m for m in mannschaften if m.spielklasse]
    for m in mit_liga:
        if any(w in m.name.lower() for w in ("1.", "erste", "herren", "damen", "aktive")):
            return m.spielklasse
    return mit_liga[0].spielklasse if mit_liga else None


def analysieren(suche: Websuche, website: str, ort: str) -> ProfilVorschlag:
    domain = domain_von(website)
    hinweise: list[str] = []

    profil = suche.strukturiert_suchen(
        query=f"Verein {domain} Mannschaften Spielklasse Mitglieder Veranstaltungen",
        objective=(
            "Vereinsprofil für eine Sponsoring-Analyse: offizieller Vereinsname, Sportarten, "
            "alle Mannschaften mit ihrer aktuellen Spielklasse, Mitgliederzahl und wiederkehrende "
            "Veranstaltungen wie Turniere oder Feste. Seiten zu Mannschaften und Verein zuerst."
        ),
        system_prompt=NICHTS_ERFINDEN,
        schema=PROFIL_SCHEMA,
        domain=domain,
    )
    sponsoren = suche.strukturiert_suchen(
        query=f"Sponsoren und Partner von {domain}",
        objective=(
            "Alle aktuellen Sponsoren und Partner des Vereins mit der jeweiligen Gegenleistung "
            "(z. B. Trikot, Bande, Ausrüster) und ihrer Website. Sponsorenseite und Logos zuerst."
        ),
        system_prompt=NICHTS_ERFINDEN
        + " Nur Unternehmen, die als Sponsor oder Partner dieses Vereins genannt sind.",
        schema=SPONSOREN_SCHEMA,
        domain=domain,
    )

    p = profil.inhalt
    mannschaften = [Mannschaft(**m) for m in p.get("mannschaften") or [] if m.get("name")]
    erkannte = []
    for s in sponsoren.inhalt.get("sponsoren") or []:
        if not s.get("firma"):
            continue
        text = s.get("gegenleistung") or None
        erkannte.append(
            ErkannterSponsor(
                firma=s["firma"],
                gegenleistung_text=text,
                gegenleistung=katalog_id(text),
                website=s.get("website") or None,
            )
        )

    if not p.get("name"):
        hinweise.append("Vereinsname nicht gefunden – bitte eintragen.")
    if not mannschaften:
        hinweise.append("Keine Mannschaften gefunden – bitte ergänzen.")
    if not erkannte:
        hinweise.append("Keine Sponsoren auf der Website erkannt – gern als Liste hochladen.")

    return ProfilVorschlag(
        name=p.get("name"),
        website=website,
        ort=ort,
        sportarten=p.get("sportarten") or [],
        mannschaften=mannschaften,
        spielklasse=hoechste_spielklasse(mannschaften),
        mitglieder=p.get("mitglieder"),
        veranstaltungen=p.get("veranstaltungen") or [],
        sponsoren=erkannte,
        inventar_vergeben=sorted({s.gegenleistung for s in erkannte if s.gegenleistung}),
        belege=profil.belege + sponsoren.belege,
        hinweise=hinweise,
    )
