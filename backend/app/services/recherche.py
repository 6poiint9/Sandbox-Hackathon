"""Recherche + Bewertung als Hintergrundaufgabe, parallel über einen kleinen Thread-Pool.

Fehler pro Kandidat werden am Kandidaten gespeichert und stoppen nie den Lauf.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from sqlmodel import Session

from app.db import engine
from app.models import Kandidat, Unternehmen, Verein
from app.providers.llm import analyse_modell
from app.providers.websuche import websuche
from app.services.bewertung import bewerten

logger = logging.getLogger(__name__)
PARALLEL = 4


def _ein_kandidat(kandidat_id: int, freie: list[str], eng=None) -> None:
    with Session(eng or engine) as session:
        k = session.get(Kandidat, kandidat_id)
        if not k:
            return
        k.recherche_status = "laeuft"
        session.add(k)
        session.commit()
        try:
            verein = session.get(Verein, k.verein_id)
            u = session.get(Unternehmen, k.unternehmen_id)
            felder = bewerten(analyse_modell(), websuche(), verein, k, u, freie)
            for feld, wert in felder.items():
                setattr(k, feld, wert)
            k.recherche_status = "fertig"
        except Exception as e:  # pro Kandidat abfangen, Lauf geht weiter
            logger.exception("Recherche fehlgeschlagen für Kandidat %s", kandidat_id)
            k.recherche_status = "fehler"
            k.recherche_fehler = str(e)[:500]
        session.add(k)
        session.commit()


def alle_recherchieren(kandidat_ids: list[int], freie: list[str], eng=None) -> None:
    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        list(pool.map(lambda kid: _ein_kandidat(kid, freie, eng), kandidat_ids))
