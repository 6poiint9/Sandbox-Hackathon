"""Import der Bestandssponsoren aus CSV (Vorlage: docs/vorlage-bestandssponsoren.csv).

Tolerant: Semikolon oder Komma, deutsche Beträge ("1.500,00 €"), Datum als
2027-06-30 oder 30.06.2027, Spaltennamen mit Varianten. Fehlerhafte Zeilen
werden gemeldet, der Rest wird importiert.
"""

import csv
import io
import re
from datetime import date, datetime

from pydantic import BaseModel

from app.models import SponsorBasis
from app.services.zuordnung import katalog_id

SPALTEN = {
    "firma": {"firma", "unternehmen", "sponsor", "name"},
    "website": {"website", "url", "homepage", "webseite"},
    "gegenleistung": {"gegenleistung", "paket", "leistung", "werbeform"},
    "betrag_eur": {"betrag_eur", "betrag", "summe", "preis", "euro"},
    "laufzeit_bis": {"laufzeit_bis", "laufzeit", "bis", "vertragsende", "ende"},
    "ansprechpartner": {"ansprechpartner", "kontakt"},
    "notiz": {"notiz", "bemerkung", "kommentar"},
}


class ImportErgebnis(BaseModel):
    sponsoren: list[SponsorBasis]
    fehler: list[str]


def _spalte(kopf: str) -> str | None:
    k = kopf.strip().lower().replace(" ", "_")
    for ziel, varianten in SPALTEN.items():
        if k in varianten:
            return ziel
    return None


def betrag(text: str) -> int | None:
    t = re.sub(r"[^\d,.]", "", text or "")
    if not t:
        return None
    if "," in t:  # deutsch: 1.500,50
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") == 1 and len(t.split(".")[1]) == 3:  # 1.500
        t = t.replace(".", "")
    return round(float(t))


def datum(text: str) -> date | None:
    t = (text or "").strip()
    if not t:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%m/%Y", "%Y"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Datum nicht lesbar: {t}")


def importieren(inhalt: bytes) -> ImportErgebnis:
    text = inhalt.decode("utf-8-sig", errors="replace")
    erste_zeile = text.splitlines()[0] if text.strip() else ""
    trenner = ";" if erste_zeile.count(";") >= erste_zeile.count(",") else ","
    leser = csv.DictReader(io.StringIO(text), delimiter=trenner)

    zuordnung = {kopf: _spalte(kopf) for kopf in (leser.fieldnames or [])}
    if "firma" not in zuordnung.values():
        return ImportErgebnis(sponsoren=[], fehler=["Spalte 'firma' fehlt in der Kopfzeile."])

    sponsoren, fehler = [], []
    for nr, zeile in enumerate(leser, start=2):
        werte = {zuordnung[k]: (v or "").strip() for k, v in zeile.items() if k and zuordnung.get(k)}
        if not werte.get("firma"):
            if any(werte.values()):
                fehler.append(f"Zeile {nr}: Firma fehlt.")
            continue
        try:
            text_leistung = werte.get("gegenleistung") or None
            sponsoren.append(
                SponsorBasis(
                    firma=werte["firma"],
                    website=werte.get("website") or None,
                    gegenleistung=katalog_id(text_leistung),
                    gegenleistung_text=text_leistung,
                    betrag_eur=betrag(werte.get("betrag_eur", "")),
                    laufzeit_bis=datum(werte.get("laufzeit_bis", "")),
                    ansprechpartner=werte.get("ansprechpartner") or None,
                    notiz=werte.get("notiz") or None,
                )
            )
        except ValueError as e:
            fehler.append(f"Zeile {nr} ({werte['firma']}): {e}")
    return ImportErgebnis(sponsoren=sponsoren, fehler=fehler)
