"""Hintergrundauftrag: Umkreissuche + Recherche der besten Kandidaten + E-Mail.

So muss niemand im Onboarding warten: Die Potenzialanalyse ist sofort da,
Karte und Kandidaten füllen sich, und wer möchte, bekommt eine Mail.
"""

import logging

from fastapi import HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine
from app.models import InventarPosten, Kandidat, Sponsor, Unternehmen, Verein
from app.services import mail, recherche
from app.services.potenzial import berechnen

logger = logging.getLogger(__name__)


def _status(verein_id: int, status: str, fehler: str | None = None, eng=None) -> None:
    with Session(eng or engine) as s:
        v = s.get(Verein, verein_id)
        v.suche_status = status
        v.suche_fehler = fehler
        s.add(v)
        s.commit()


def ausfuehren(verein_id: int, anzahl_recherche: int = 10, eng=None) -> None:
    from app.routers.kandidaten import freie_inventar_ids, kandidaten_suchen

    eng = eng or engine
    try:
        with Session(eng) as s:
            kandidaten_suchen(verein_id, 30, s)
            offen = s.exec(
                select(Kandidat).where(Kandidat.verein_id == verein_id, Kandidat.recherche_status == "offen")
            ).all()
            offen = sorted(offen, key=lambda k: (-k.vorfilter_score, k.entfernung_km))[:anzahl_recherche]
            for k in offen:
                k.recherche_status = "wartet"
                s.add(k)
            s.commit()
            ids = [k.id for k in offen]
            freie, _ = freie_inventar_ids(s, verein_id)
        recherche.alle_recherchieren(ids, freie, eng)
        _status(verein_id, "fertig", eng=eng)
        benachrichtigen(verein_id, eng)
    except HTTPException as e:
        logger.warning("Analyse für Verein %s fehlgeschlagen: %s", verein_id, e.detail)
        _status(verein_id, "fehler", str(e.detail), eng=eng)
    except Exception as e:  # Hintergrundauftrag darf nie still sterben
        logger.exception("Analyse für Verein %s fehlgeschlagen", verein_id)
        _status(verein_id, "fehler", str(e)[:300], eng=eng)


def benachrichtigen(verein_id: int, eng=None) -> bool:
    with Session(eng or engine) as s:
        v = s.get(Verein, verein_id)
        if not v or not v.benachrichtigung_email or not mail.verfuegbar():
            return False
        inventar = s.exec(select(InventarPosten).where(InventarPosten.verein_id == verein_id)).all()
        sponsoren = s.exec(select(Sponsor).where(Sponsor.verein_id == verein_id)).all()
        p = berechnen(v, list(inventar), list(sponsoren))
        zeilen = s.exec(
            select(Kandidat, Unternehmen)
            .join(Unternehmen, Kandidat.unternehmen_id == Unternehmen.id)
            .where(Kandidat.verein_id == verein_id, Kandidat.recherche_status == "fertig")
        ).all()
        top = sorted(zeilen, key=lambda z: -(z[0].score or 0))[:3]
        text = mail.analyse_fertig_text(
            v.name,
            f"{get_settings().frontend_url}/#/verein/{verein_id}",
            (p.spanne_min, p.spanne_max),
            [(u.name, k.score or 0, u.branche) for k, u in top],
        )
        return mail.senden(v.benachrichtigung_email, f"Eure Sponsoring-Potenzialanalyse für {v.name} ist fertig", text)
