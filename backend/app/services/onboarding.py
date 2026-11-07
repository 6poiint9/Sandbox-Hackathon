"""Onboarding: Vereinswebsite auslesen und einen Profilvorschlag bauen.

Parallel:
- Exa zieht Profil, Sponsoren (Text) und Sportstätte direkt aus den Seiten
  (outputSchema, nur auf der Vereinsdomain) – je Feld mit Quellen und Sicherheit.
- Logo-Erkennung liest die Sponsorenseite als Bilder (Gemini), weil viele
  Sponsoren nur als Logo auftauchen.
Die Sportstätte (nicht das Impressum!) wird geokodiert und ist Mittelpunkt der Karte.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from pydantic import BaseModel

from app.providers.websuche import Beleg, StrukturierteAntwort, Websuche
from app.services import geo, logos
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

SPORTSTAETTE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "strasse": {"type": "string"},
        "plz": {"type": "string"},
        "ort": {"type": "string"},
    },
}


class Mannschaft(BaseModel):
    name: str
    spielklasse: str | None = None


class ErkannterSponsor(BaseModel):
    firma: str
    gegenleistung_text: str | None = None
    gegenleistung: str | None = None  # katalog_id
    website: str | None = None
    logo_url: str | None = None
    quelle: str = "text"  # "text", "logo" oder "text+logo"


class ProfilVorschlag(BaseModel):
    name: str | None = None
    website: str
    ort: str
    sportstaette: str | None = None
    lat: float | None = None
    lon: float | None = None
    sportarten: list[str] = []
    mannschaften: list[Mannschaft] = []
    spielklasse: str | None = None
    mitglieder: int | None = None
    veranstaltungen: list[str] = []
    sponsoren: list[ErkannterSponsor] = []
    sponsorenseite: str | None = None
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


def _norm(text: str) -> str:
    t = text.lower()
    t = re.sub(r"\b(gmbh|ag|kg|e\.?k\.?|eg|co|ohg|mbh|gbr|inh\.?)\b", "", t)
    return re.sub(r"[^a-z0-9äöüß]", "", t)


def _gleich(a: ErkannterSponsor, b: ErkannterSponsor) -> bool:
    na, nb = _norm(a.firma), _norm(b.firma)
    if len(na) >= 4 and len(nb) >= 4 and (na in nb or nb in na):
        return True
    if a.website and b.website:
        return domain_von(a.website) == domain_von(b.website)
    return False


def sponsoren_zusammenfuehren(text: list[ErkannterSponsor], logo: list[ErkannterSponsor]) -> list[ErkannterSponsor]:
    ergebnis = list(text)
    for l in logo:
        treffer = next((t for t in ergebnis if _gleich(t, l)), None)
        if treffer:
            treffer.quelle = "text+logo"
            treffer.logo_url = treffer.logo_url or l.logo_url
            treffer.website = treffer.website or l.website
        else:
            ergebnis.append(l)
    return ergebnis


def _sportstaette_text(s: dict) -> str | None:
    teile = [s.get("name"), s.get("strasse"), " ".join(filter(None, [s.get("plz"), s.get("ort")]))]
    text = ", ".join(t.strip() for t in teile if t and t.strip())
    return text or None


def _verorten(s: dict, ort: str) -> tuple[float | None, float | None, str | None]:
    """Sportstätte geokodieren; sonst Ort. Gibt (lat, lon, Hinweis) zurück."""
    versuche = []
    if s.get("strasse") and (s.get("ort") or ort):
        versuche.append(f"{s['strasse']}, {s.get('plz') or ''} {s.get('ort') or ort}")
    if s.get("name") and (s.get("ort") or ort):
        versuche.append(f"{s['name']}, {s.get('ort') or ort}")
    for q in versuche:
        try:
            lat, lon = geo.geokodieren(q)
            return lat, lon, None
        except geo.GeoFehler:
            continue
    if ort:
        try:
            lat, lon = geo.geokodieren(ort)
            return lat, lon, "Sportstätte nicht gefunden – Kartenmittelpunkt ist der Ort. Bitte Adresse prüfen."
        except geo.GeoFehler:
            pass
    return None, None, "Standort nicht gefunden – bitte Adresse der Sportstätte eintragen."


def analysieren(suche: Websuche, website: str, ort: str = "", logo_erkennung: bool = True) -> ProfilVorschlag:
    domain = domain_von(website)
    hinweise: list[str] = []

    def profil() -> StrukturierteAntwort:
        return suche.strukturiert_suchen(
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

    def sponsoren_text() -> StrukturierteAntwort:
        return suche.strukturiert_suchen(
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

    def sportstaette() -> StrukturierteAntwort:
        return suche.strukturiert_suchen(
            query=f"Sportplatz Stadion Anfahrt {domain}",
            objective=(
                "Name und Adresse der Sportstätte, auf der der Verein seine Heimspiele austrägt "
                "(Stadion, Sportplatz, Sporthalle oder Vereinsheim). Anfahrts- und Kontaktseiten zuerst."
            ),
            system_prompt=NICHTS_ERFINDEN
            + " Nur die Adresse der Sportstätte oder des Vereinsheims. NICHT die Adresse aus dem "
            "Impressum oder von Vorstandsmitgliedern – das sind oft Privatadressen.",
            schema=SPORTSTAETTE_SCHEMA,
            domain=domain,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_profil, f_sponsoren, f_staette = pool.submit(profil), pool.submit(sponsoren_text), pool.submit(sportstaette)
        f_logos = pool.submit(logos.sponsoren_aus_logos, website) if logo_erkennung else None
        p_ant, s_ant, st_ant = f_profil.result(), f_sponsoren.result(), f_staette.result()
        logo_sponsoren, sponsorenseite = f_logos.result() if f_logos else ([], None)

    p = p_ant.inhalt
    mannschaften = [Mannschaft(**m) for m in p.get("mannschaften") or [] if m.get("name")]
    aus_text = []
    for s in s_ant.inhalt.get("sponsoren") or []:
        if not s.get("firma"):
            continue
        text = s.get("gegenleistung") or None
        aus_text.append(
            ErkannterSponsor(firma=s["firma"], gegenleistung_text=text, gegenleistung=katalog_id(text),
                             website=s.get("website") or None)
        )
    aus_logos = [
        ErkannterSponsor(firma=l.firma, website=l.website, logo_url=l.logo_url, quelle="logo")
        for l in logo_sponsoren
    ]
    erkannte = sponsoren_zusammenfuehren(aus_text, aus_logos)

    staette = st_ant.inhalt or {}
    ort_final = ort.strip() or (staette.get("ort") or "").strip()
    lat, lon, standort_hinweis = _verorten(staette, ort_final)
    if standort_hinweis:
        hinweise.append(standort_hinweis)
    if not p.get("name"):
        hinweise.append("Vereinsname nicht gefunden – bitte eintragen.")
    if not mannschaften:
        hinweise.append("Keine Mannschaften gefunden – bitte ergänzen.")
    if not erkannte:
        hinweise.append("Keine Sponsoren auf der Website erkannt – gern als Liste hochladen.")

    return ProfilVorschlag(
        name=p.get("name"),
        website=website,
        ort=ort_final,
        sportstaette=_sportstaette_text(staette),
        lat=lat,
        lon=lon,
        sportarten=p.get("sportarten") or [],
        mannschaften=mannschaften,
        spielklasse=hoechste_spielklasse(mannschaften),
        mitglieder=p.get("mitglieder"),
        veranstaltungen=p.get("veranstaltungen") or [],
        sponsoren=erkannte,
        sponsorenseite=sponsorenseite,
        inventar_vergeben=sorted({s.gegenleistung for s in erkannte if s.gegenleistung}),
        belege=p_ant.belege + s_ant.belege + st_ant.belege,
        hinweise=hinweise,
    )
