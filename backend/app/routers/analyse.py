"""Potenzialanalyse, Ansprache und CSV-Export."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from app.db import get_session
from app.models import Ansprache, AssetVergabe, InventarPosten, Kandidat, Sponsor, Unternehmen, Verein
from app.providers.cache import DemoDatenFehlen
from app.providers.llm import SprachmodellFehler, text_modell
from app.services import ansprache as ansprache_service
from app.services.plan import Finanzierungsplan, planen
from app.services.potenzial import Potenzial, berechnen

router = APIRouter(tags=["analyse"])


def _verein(session: Session, verein_id: int) -> Verein:
    v = session.get(Verein, verein_id)
    if not v:
        raise HTTPException(404, "Verein nicht gefunden")
    return v


def _potenzial(session: Session, verein: Verein) -> Potenzial:
    inventar = session.exec(select(InventarPosten).where(InventarPosten.verein_id == verein.id)).all()
    sponsoren = session.exec(select(Sponsor).where(Sponsor.verein_id == verein.id)).all()
    ids = [p.id for p in inventar]
    vergaben = session.exec(select(AssetVergabe).where(AssetVergabe.asset_id.in_(ids))).all() if ids else []
    return berechnen(verein, list(inventar), list(sponsoren), list(vergaben))


@router.get("/vereine/{verein_id}/potenzial", response_model=Potenzial)
def potenzial(verein_id: int, session: Session = Depends(get_session)) -> Potenzial:
    return _potenzial(session, _verein(session, verein_id))


@router.get("/vereine/{verein_id}/plan", response_model=Finanzierungsplan)
def finanzierungsplan(verein_id: int, session: Session = Depends(get_session)) -> Finanzierungsplan:
    """Plan für das Ziel (verein.ziel_eur, inkl. Bestand) aus den freien Paketen, mit Kandidaten."""
    verein = _verein(session, verein_id)
    kandidaten = session.exec(
        select(Kandidat, Unternehmen)
        .join(Unternehmen, Kandidat.unternehmen_id == Unternehmen.id)
        .where(Kandidat.verein_id == verein_id)
    ).all()
    return planen(_potenzial(session, verein), verein.ziel_eur, [(k, u) for k, u in kandidaten])


@router.get("/kandidaten/{kandidat_id}/ansprache", response_model=Ansprache)
def ansprache_lesen(kandidat_id: int, session: Session = Depends(get_session)) -> Ansprache:
    a = session.exec(select(Ansprache).where(Ansprache.kandidat_id == kandidat_id)).first()
    if not a:
        raise HTTPException(404, "Noch keine Ansprache erzeugt")
    return a


@router.post("/kandidaten/{kandidat_id}/ansprache", response_model=Ansprache)
def ansprache_erzeugen(
    kandidat_id: int, neu: bool = False, session: Session = Depends(get_session)
) -> Ansprache:
    k = session.get(Kandidat, kandidat_id)
    if not k:
        raise HTTPException(404, "Kandidat nicht gefunden")
    vorhanden = session.exec(select(Ansprache).where(Ansprache.kandidat_id == kandidat_id)).first()
    if vorhanden and not neu:
        return vorhanden
    if k.recherche_status != "fertig":
        raise HTTPException(409, "Kandidat ist noch nicht recherchiert")
    try:
        text = ansprache_service.erzeugen(
            text_modell(), session.get(Verein, k.verein_id), k, session.get(Unternehmen, k.unternehmen_id)
        )
    except (SprachmodellFehler, DemoDatenFehlen) as e:
        raise HTTPException(502, str(e)) from e
    a = vorhanden or Ansprache(kandidat_id=kandidat_id, **text.model_dump())
    for feld, wert in text.model_dump().items():
        setattr(a, feld, wert)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


@router.get("/vereine/{verein_id}/export")
def export(verein_id: int, session: Session = Depends(get_session)) -> Response:
    """Alle Kandidaten als CSV (Semikolon, UTF-8 mit BOM, öffnet sauber in Excel)."""
    verein = _verein(session, verein_id)
    zeilen = session.exec(
        select(Kandidat, Unternehmen)
        .join(Unternehmen, Kandidat.unternehmen_id == Unternehmen.id)
        .where(Kandidat.verein_id == verein_id)
    ).all()
    zeilen = sorted(zeilen, key=lambda z: -(z[0].score or z[0].vorfilter_score))

    puffer = io.StringIO()
    w = csv.writer(puffer, delimiter=";")
    w.writerow(["Unternehmen", "Branche", "Adresse", "Website", "Entfernung km", "Score", "Sicherheit",
                "Paket", "Richtpreis min", "Richtpreis max", "Status", "Gründe", "Quellen"])
    for k, u in zeilen:
        pe = k.paket_empfehlung or {}
        preis = pe.get("preis_eur") or {}
        w.writerow([
            u.name, u.branche, u.adresse or "", u.website or "", f"{k.entfernung_km:.1f}".replace(".", ","),
            k.score if k.score is not None else "", k.sicherheit or "",
            ", ".join(pe.get("namen", [])), preis.get("min", ""), preis.get("max", ""), k.status,
            " | ".join(g["text"] for g in k.gruende), " ".join(g["quelle_url"] for g in k.gruende),
        ])
    dateiname = "".join(ch if ch.isalnum() else "_" for ch in verein.name).strip("_") or "verein"
    return Response(
        content="﻿" + puffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="sponsorenkompass_{dateiname}.csv"'},
    )
