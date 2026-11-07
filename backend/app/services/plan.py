"""Finanzierungsplan: Wie erreicht der Verein sein Sponsoring-Ziel?

Reine Rechnung ohne KI (CLAUDE.md: Rechnen macht der Code).

- Ziel gilt inklusive Bestand: Lücke = Ziel − Summe der Bestandssponsoren.
- Jede freie Einheit eines Pakets ist ein möglicher neuer Sponsor.
- Strategie "Hauptsponsor + Partner": Schließt eine einzelne Einheit die
  Restlücke, wird die kleinste solche Einheit genommen. Sonst die größte
  verbleibende, die erste davon ist der Anker (Hauptsponsor). Gerechnet wird
  mit der Mitte der Preisspanne.
- Zu jeder Planzeile die besten Kandidaten: zuerst recherchierte, deren
  Paket-Empfehlung passt, dann vorgefilterte ("noch nicht geprüft").
"""

from typing import Literal

from pydantic import BaseModel

from app.models import Kandidat, Unternehmen
from app.services.potenzial import Paket, Potenzial

KANDIDATEN_JE_ZEILE = 3
AUSGESCHLOSSENE_STATUS = {"absage", "zusage"}

PlanStatus = Literal["ohne_ziel", "erreicht", "erreichbar", "knapp", "ueber_potenzial"]


class PlanKandidat(BaseModel):
    kandidat_id: int
    name: str
    score: int | None
    geprueft: bool


class PlanZeile(BaseModel):
    katalog_id: str
    name: str
    anzahl: int
    min: int
    max: int
    kandidaten: list[PlanKandidat]


class Finanzierungsplan(BaseModel):
    ziel_eur: int | None
    bestand_eur: int
    luecke_eur: int | None
    potenzial_min: int
    potenzial_max: int
    status: PlanStatus
    zeilen: list[PlanZeile]
    summe_min: int
    summe_max: int
    neue_sponsoren: int
    hebel: list[str]


class _Einheit(BaseModel):
    paket: Paket
    min: int
    max: int

    @property
    def mitte(self) -> float:
        return (self.min + self.max) / 2


def _einheiten(pakete: list[Paket]) -> list[_Einheit]:
    """Zerlegt jedes Paket in seine freien Einheiten (z. B. 4 Banden → 4 Einheiten)."""
    einheiten = []
    for p in pakete:
        n = max(p.einheiten_frei, 1)
        einheiten.extend(_Einheit(paket=p, min=p.min // n, max=p.max // n) for _ in range(n))
    return einheiten


def _auswaehlen(einheiten: list[_Einheit], luecke: int) -> list[_Einheit]:
    verbleibend = sorted(einheiten, key=lambda e: -e.mitte)
    auswahl: list[_Einheit] = []
    rest = float(luecke)
    while rest > 0 and verbleibend:
        schliesst = [e for e in verbleibend if e.mitte >= rest]
        # Schließt eine Einheit allein die Lücke: die kleinste davon. Sonst die größte (Anker zuerst).
        e = min(schliesst, key=lambda x: x.mitte) if schliesst else verbleibend[0]
        auswahl.append(e)
        verbleibend = [x for x in verbleibend if x is not e]
        rest -= e.mitte
    return auswahl


def _kandidaten_fuer(
    katalog_id: str, kandidaten: list[tuple[Kandidat, Unternehmen]], vergeben: set[int]
) -> list[PlanKandidat]:
    geprueft, vorgefiltert = [], []
    for k, u in kandidaten:
        if k.id is None or k.status in AUSGESCHLOSSENE_STATUS:
            continue
        pe = k.paket_empfehlung or {}
        if k.recherche_status == "fertig" and katalog_id in pe.get("katalog_ids", []):
            geprueft.append(PlanKandidat(kandidat_id=k.id, name=u.name, score=k.score, geprueft=True))
        elif k.recherche_status != "fertig" and katalog_id in pe.get("passende_pakete", []):
            vorgefiltert.append(
                PlanKandidat(kandidat_id=k.id, name=u.name, score=k.vorfilter_score, geprueft=False)
            )
    geprueft.sort(key=lambda c: -(c.score or 0))
    vorgefiltert.sort(key=lambda c: -(c.score or 0))
    reihenfolge = geprueft + vorgefiltert
    # Möglichst verschiedene Firmen über die Zeilen verteilen, Mehrfachnennung nur als Notlösung.
    frisch = [c for c in reihenfolge if c.kandidat_id not in vergeben]
    schon = [c for c in reihenfolge if c.kandidat_id in vergeben]
    auswahl = (frisch + schon)[:KANDIDATEN_JE_ZEILE]
    vergeben.update(c.kandidat_id for c in auswahl)
    return auswahl


def _hebel(status: PlanStatus, luecke: int, potenzial: Potenzial, rest: list[_Einheit]) -> list[str]:
    if status == "ueber_potenzial":
        fehlt = luecke - potenzial.spanne_max
        return [
            f"Eure freien Pakete bringen höchstens {potenzial.spanne_max} €, es fehlen etwa {fehlt} €.",
            "Weitere Assets anbieten, z. B. Turniere, Social Media oder eine Azubi-Kooperation.",
            "Spielklasse und Zuschauerzahl im Profil prüfen, sie bestimmen den Preisfaktor.",
            "Das Ziel auf zwei Saisons verteilen oder mehrjährige Verträge anbieten.",
        ]
    if status == "knapp":
        hebel = ["Erreichbar, wenn die Preise eher am oberen Rand liegen: im Gespräch mit dem Einstiegspreis beginnen."]
        if rest:
            reserve = max(rest, key=lambda e: e.mitte).paket.name
            hebel.append(f"Als Reserve ein weiteres Paket anbieten: {reserve}.")
        return hebel
    return []


def planen(
    potenzial: Potenzial,
    ziel_eur: int | None,
    kandidaten: list[tuple[Kandidat, Unternehmen]],
) -> Finanzierungsplan:
    """Stellt aus den freien Paketen einen Plan für das Ziel zusammen."""
    basis = {
        "ziel_eur": ziel_eur,
        "bestand_eur": potenzial.bestand_eur,
        "potenzial_min": potenzial.spanne_min,
        "potenzial_max": potenzial.spanne_max,
    }
    leer = {"zeilen": [], "summe_min": 0, "summe_max": 0, "neue_sponsoren": 0, "hebel": []}
    if not ziel_eur:
        return Finanzierungsplan(**basis, luecke_eur=None, status="ohne_ziel", **leer)
    luecke = ziel_eur - potenzial.bestand_eur
    if luecke <= 0:
        return Finanzierungsplan(**basis, luecke_eur=luecke, status="erreicht", **leer)

    einheiten = _einheiten(potenzial.freie_pakete)
    auswahl = _auswaehlen(einheiten, luecke)
    gewaehlt = {id(e) for e in auswahl}  # gleiche Einheiten (4 Banden) sind gleich, daher Identität
    rest = [e for e in einheiten if id(e) not in gewaehlt]
    summe_min = sum(e.min for e in auswahl)
    summe_max = sum(e.max for e in auswahl)
    if summe_max < luecke:
        status: PlanStatus = "ueber_potenzial"
    elif summe_min >= luecke:
        status = "erreichbar"
    else:
        status = "knapp"

    zeilen: list[PlanZeile] = []
    vergeben: set[int] = set()
    for e in auswahl:
        zeile = next((z for z in zeilen if z.katalog_id == e.paket.katalog_id), None)
        if zeile:
            zeile.anzahl += 1
            zeile.min += e.min
            zeile.max += e.max
            continue
        zeilen.append(PlanZeile(katalog_id=e.paket.katalog_id, name=e.paket.name, anzahl=1,
                                min=e.min, max=e.max, kandidaten=[]))
    for z in zeilen:
        z.kandidaten = _kandidaten_fuer(z.katalog_id, kandidaten, vergeben)

    return Finanzierungsplan(
        **basis,
        luecke_eur=luecke,
        status=status,
        zeilen=zeilen,
        summe_min=summe_min,
        summe_max=summe_max,
        neue_sponsoren=len(auswahl),
        hebel=_hebel(status, luecke, potenzial, rest),
    )
