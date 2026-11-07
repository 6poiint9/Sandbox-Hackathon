"""Freemium: Ohne Abo sind die besten 3 Kandidaten frei, der Rest ist gesperrt.

Die Sperre gilt auf dem Server, nicht nur in der Oberfläche: Gesperrte Kandidaten
werden ohne Namen, Adresse, Website, Gründe und Quellen ausgeliefert, und jeder
Endpunkt mit ihrer ID antwortet mit 402 (siehe auth.zugriff).

"Die besten 3" = Reihenfolge des Vorfilters (Score, dann Entfernung). Sie steht
schon vor der Recherche fest und ändert sich nicht, wenn Ergebnisse eintreffen;
genau diese 3 werden ohne Abo recherchiert.
"""

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import Kandidat

FREI_ANZAHL = 3
ABO_PREIS_EUR = 169  # pro Jahr, Demo ohne Zahlung
GESPERRT_NAME = "Gesperrter Betrieb"


def reihenfolge(k: Kandidat) -> tuple[int, float]:
    return (-k.vorfilter_score, k.entfernung_km)


def freie_ids(session: Session, verein_id: int) -> set[int]:
    kandidaten = session.exec(select(Kandidat).where(Kandidat.verein_id == verein_id)).all()
    return {k.id for k in sorted(kandidaten, key=reihenfolge)[:FREI_ANZAHL]}


def pruefen(session: Session, kandidat_id: int) -> None:
    """402, wenn der Kandidat ohne Abo nicht freigeschaltet ist."""
    k = session.get(Kandidat, kandidat_id)
    if k and kandidat_id not in freie_ids(session, k.verein_id):
        raise HTTPException(402, "Dieser Betrieb ist mit dem Abo sichtbar.")
