"""Grober Vorfilter vor der kostenpflichtigen Recherche.

Score 0–100, bewusst einfach und erklärbar:
- Branche: bis 25 Punkte nach Sponsoring-Nähe (Erfahrungswert, zu validieren)
  plus bis 20 Punkte für passende FREIE Inventarposten
- Nähe zum Verein: bis 30 Punkte
- Branche ist eine Lücke (kein Bestandssponsor dieser Branche): 15 Punkte
- Website vorhanden (nötig für die Recherche): 10 Punkte
Bestandssponsoren und überregionale Ketten im Handel/in der Gastronomie
werden ausgeschlossen.
"""

import re
from collections import Counter

# Wie häufig Betriebe dieser Branche lokale Vereine sponsern (0–1).
# Erfahrungswert aus der Vereinspraxis, in Gesprächen mit Vorständen prüfen.
SPONSORING_NAEHE: dict[str, float] = {
    "Autohäuser": 1.0, "Banken": 1.0, "Stadtwerke": 1.0, "Versicherungen": 0.9,
    "Bäckereien": 0.9, "Handwerk": 0.9, "Brauerei": 0.9, "Getränkehandel": 0.8,
    "Sportfachhandel": 0.8, "Familienbetriebe": 0.8, "Apotheken": 0.7, "Optiker": 0.7,
    "Physio": 0.7, "Druckerei": 0.7, "Logistik": 0.7, "Fitness": 0.6,
    "Gastronomie": 0.6, "Handel": 0.5, "Dienstleister": 0.5, "Pflege": 0.5,
}
# Ketten sponsern in diesen Branchen kaum lokal (Banken, Autohäuser dagegen schon).
KETTE_AUSSCHLIESSEN = {"Handel", "Gastronomie", "Fitness", "Optiker", "Apotheken", "Dienstleister"}

from pydantic import BaseModel

from app.data import katalog
from app.services.osm import Betrieb

# Unsere OSM-Branche passt auch zu diesen Katalog-Zielbranchen.
VERWANDT: dict[str, set[str]] = {
    "Bäckereien": {"Handel", "lokaler Handel", "Familienbetriebe"},
    "Handel": {"lokaler Handel"},
    "Handwerk": {"Familienbetriebe"},
    "Gastronomie": {"Familienbetriebe"},
    "Apotheken": {"Familienbetriebe", "lokaler Handel"},
    "Optiker": {"Familienbetriebe", "lokaler Handel", "Handel"},
    "Getränkehandel": {"Getränke", "Handel"},
    "Brauerei": {"Getränke", "Getränkehandel"},
    "Autohäuser": {"große Arbeitgeber"},
    "Banken": {"große Arbeitgeber"},
    "Stadtwerke": {"große Arbeitgeber"},
    "Physio": {"Fitness"},
    "Fitness": {"junge Marken"},
}

# Branche eines Bestandssponsors aus dem Firmennamen erraten.
SPONSOR_BRANCHE: list[tuple[str, str]] = [
    (r"bäcker|backhaus|backstube", "Bäckereien"),
    (r"autohaus|automobil|kfz|auto\b|reifen", "Autohäuser"),
    (r"sparkasse|volksbank|raiffeisen|bank", "Banken"),
    (r"apotheke", "Apotheken"),
    (r"optik|optiker", "Optiker"),
    (r"versicherung|allianz|ergo\b|axa|lvm|provinzial|signal iduna", "Versicherungen"),
    (r"stadtwerk|energie|badenova", "Stadtwerke"),
    (r"brauerei|bräu", "Brauerei"),
    (r"getränke", "Getränkehandel"),
    (r"physio", "Physio"),
    (r"fitness", "Fitness"),
    (r"metzger|fleischer", "Familienbetriebe"),
    (r"gasthaus|restaurant|café|cafe|pizzeria|gaststätte|hotel", "Gastronomie"),
    (r"druck", "Druckerei"),
    (r"sanitär|elektro|maler|bau|schreiner|dach|heizung|zimmerei|installat|fliesen", "Handwerk"),
    (r"fahrschule|steuer|kanzlei|immobilien", "Dienstleister"),
]


class Vorgefiltert(BaseModel):
    betrieb: Betrieb
    score: int
    gruende: list[str]
    passende_pakete: list[str]


class Vorfilterergebnis(BaseModel):
    kandidaten: list[Vorgefiltert]
    luecken: list[dict]  # [{"branche": ..., "betriebe": n}]
    betriebe_gesamt: int
    ausgeschlossen_bestand: int


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]", "", text.lower())


def sponsor_branche(firma: str) -> str | None:
    klein = firma.lower()
    for muster, branche in SPONSOR_BRANCHE:
        if re.search(muster, klein):
            return branche
    return None


def ist_bestandssponsor(name: str, sponsoren_namen: list[str]) -> bool:
    n = _norm(name)
    for s in sponsoren_namen:
        sn = _norm(s)
        if len(sn) >= 5 and len(n) >= 5 and (sn in n or n in sn):
            return True
    return False


def passende_pakete(branche: str, freie_ids: list[str]) -> list[str]:
    eintraege = katalog.nach_id()
    passend = {branche} | VERWANDT.get(branche, set())
    return [k for k in freie_ids if passend & set(eintraege[k]["zielbranchen"])]


def filtern(
    betriebe: list[Betrieb],
    freie_ids: list[str],
    sponsoren_namen: list[str],
    radius_km: float,
    anzahl: int = 30,
) -> Vorfilterergebnis:
    abgedeckt = {b for b in (sponsor_branche(s) for s in sponsoren_namen) if b}
    ohne_bestand = [b for b in betriebe if not ist_bestandssponsor(b.name, sponsoren_namen)]

    bewertet: list[Vorgefiltert] = []
    for b in ohne_bestand:
        if b.kette and b.branche in KETTE_AUSSCHLIESSEN:
            continue
        pakete = passende_pakete(b.branche, freie_ids)
        gruende: list[str] = []
        naehe_branche = SPONSORING_NAEHE.get(b.branche, 0.5)
        # 25 Punkte für die Sponsoring-Nähe der Branche, 20 für passende freie Pakete
        punkte_branche = round(25 * naehe_branche + 10 * min(len(pakete), 2)) if pakete else 0
        if pakete:
            gruende.append(f"Branche {b.branche} passt zu {len(pakete)} freien Paketen")
        nah = max(0.0, 1 - b.entfernung_km / max(radius_km, 0.1))
        punkte_naehe = round(30 * nah)
        gruende.append(f"{b.entfernung_km:.1f} km entfernt")
        punkte_luecke = 0
        if b.branche not in abgedeckt and pakete:
            punkte_luecke = 15
            gruende.append(f"Noch kein Sponsor aus der Branche {b.branche}")
        punkte_web = 10 if b.website else 0
        if not b.website:
            gruende.append("Keine Website in OpenStreetMap")
        score = punkte_branche + punkte_naehe + punkte_luecke + punkte_web
        bewertet.append(Vorgefiltert(betrieb=b, score=score, gruende=gruende, passende_pakete=pakete))

    bewertet.sort(key=lambda v: (-v.score, v.betrieb.entfernung_km))

    # Vielfalt: höchstens ein Fünftel der Plätze für dieselbe Branche
    grenze = max(3, anzahl // 5)
    je_branche: Counter[str] = Counter()
    auswahl: list[Vorgefiltert] = []
    for v in bewertet:
        if je_branche[v.betrieb.branche] >= grenze:
            continue
        auswahl.append(v)
        je_branche[v.betrieb.branche] += 1
        if len(auswahl) >= anzahl:
            break

    gesuchte = {zb for k in freie_ids for zb in katalog.nach_id()[k]["zielbranchen"]}
    vorhanden = Counter(
        b.branche for b in ohne_bestand if not (b.kette and b.branche in KETTE_AUSSCHLIESSEN)
    )
    luecken = [
        {"branche": br, "betriebe": n}
        for br, n in vorhanden.most_common()
        if br not in abgedeckt and (br in gesuchte or VERWANDT.get(br, set()) & gesuchte)
    ]

    return Vorfilterergebnis(
        kandidaten=auswahl,
        luecken=luecken,
        betriebe_gesamt=len(betriebe),
        ausgeschlossen_bestand=len(betriebe) - len(ohne_bestand),
    )
