"""Verein, Angebots-Inventar und Bestandssponsoren."""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.data import katalog
from app.db import get_session
from app.models import InventarPosten, Konto, Sponsor, SponsorBasis, Verein, VereinBasis
from app.services.auth import Inhaber, inhaber
from app.services import potenzial
from app.services.csv_import import importieren

router = APIRouter(tags=["vereine"])


def _verein(session: Session, verein_id: int) -> Verein:
    verein = session.get(Verein, verein_id)
    if not verein:
        raise HTTPException(404, "Verein nicht gefunden")
    return verein


# --- Verein -----------------------------------------------------------------


class ZielVorschlag(BaseModel):
    min: int
    max: int
    vorschlag: int
    erklaerung: str


@router.get("/richtwerte/ziel", response_model=ZielVorschlag | None)
def ziel_vorschlag(mitglieder: int = Query(ge=1, le=100000), spielklasse: str | None = Query(None, max_length=80)):
    """Übliches Sponsoring pro Saison aus Mitgliederzahl und Spielklasse (Richtwert fürs Ziel)."""
    mw = potenzial.marktwert(Verein(name="-", ort="-", mitglieder=mitglieder, spielklasse=spielklasse))
    if not mw:
        return None
    lo, hi = potenzial.EURO_JE_MITGLIED
    return ZielVorschlag(
        min=mw[0], max=mw[1], vorschlag=int(round((mw[0] + mw[1]) / 2 / 500) * 500),
        erklaerung=f"{mitglieder} Mitglieder × {lo}–{hi} € je Mitglied, angepasst an die Spielklasse "
        "(Marktdaten: motivation4teams, VSA/DSHS)",
    )



@router.post("/vereine", response_model=Verein)
def verein_anlegen(
    daten: VereinBasis,
    session: Session = Depends(get_session),
    wer: Inhaber = Depends(inhaber),
) -> Verein:
    verein = Verein.model_validate(daten)
    # Angemeldet: gehört dem Konto. Gast: gehört dem Gast-Cookie, bis er sich anmeldet.
    verein.konto_id = wer.konto.id if wer.konto else None
    verein.gast_hash = None if wer.konto else wer.gast_hash
    session.add(verein)
    session.commit()
    session.refresh(verein)
    return verein


@router.get("/vereine/{verein_id}", response_model=Verein)
def verein_lesen(verein_id: int, session: Session = Depends(get_session)) -> Verein:
    return _verein(session, verein_id)


@router.patch("/vereine/{verein_id}", response_model=Verein)
def verein_aendern(
    verein_id: int, daten: dict, session: Session = Depends(get_session)
) -> Verein:
    verein = _verein(session, verein_id)
    erlaubt = set(VereinBasis.model_fields) - {"suche_status", "suche_fehler"}
    for feld, wert in daten.items():
        if feld in erlaubt:
            setattr(verein, feld, wert)
    Verein.model_validate(verein)
    session.add(verein)
    session.commit()
    session.refresh(verein)
    return verein


# --- Inventar ---------------------------------------------------------------


class InventarEintrag(BaseModel):
    katalog_id: str
    verfuegbar: bool = True
    vergeben_an: int | None = None
    preis_eur: int | None = None
    anzahl: int = Field(default=1, ge=1, le=999)
    belegt_manuell: int = Field(default=0, ge=0, le=999)


@router.get("/vereine/{verein_id}/inventar", response_model=list[InventarPosten])
def inventar_lesen(verein_id: int, session: Session = Depends(get_session)):
    _verein(session, verein_id)
    return session.exec(select(InventarPosten).where(InventarPosten.verein_id == verein_id)).all()


@router.put("/vereine/{verein_id}/inventar", response_model=list[InventarPosten])
def inventar_setzen(
    verein_id: int, eintraege: list[InventarEintrag], session: Session = Depends(get_session)
):
    """Ersetzt das Inventar komplett (Häkchenliste aus dem Onboarding)."""
    _verein(session, verein_id)
    bekannt = katalog.nach_id()
    unbekannt = [e.katalog_id for e in eintraege if e.katalog_id not in bekannt]
    if unbekannt:
        raise HTTPException(422, f"Unbekannte Katalog-IDs: {', '.join(unbekannt)}")
    for alt in session.exec(select(InventarPosten).where(InventarPosten.verein_id == verein_id)):
        session.delete(alt)
    neu = [InventarPosten(verein_id=verein_id, **e.model_dump()) for e in eintraege]
    session.add_all(neu)
    session.commit()
    for p in neu:
        session.refresh(p)
    return neu


# --- Sponsoren --------------------------------------------------------------


@router.get("/vereine/{verein_id}/sponsoren", response_model=list[Sponsor])
def sponsoren_lesen(verein_id: int, session: Session = Depends(get_session)):
    _verein(session, verein_id)
    return session.exec(select(Sponsor).where(Sponsor.verein_id == verein_id)).all()


@router.post("/vereine/{verein_id}/sponsoren", response_model=list[Sponsor])
def sponsoren_anlegen(
    verein_id: int, daten: list[SponsorBasis], session: Session = Depends(get_session)
):
    _verein(session, verein_id)
    neu = [Sponsor(verein_id=verein_id, **d.model_dump()) for d in daten]
    session.add_all(neu)
    session.commit()
    for s in neu:
        session.refresh(s)
    return neu


class ImportAntwort(BaseModel):
    importiert: list[Sponsor]
    fehler: list[str]


@router.post("/vereine/{verein_id}/sponsoren/import", response_model=ImportAntwort)
async def sponsoren_importieren(
    verein_id: int, datei: UploadFile, session: Session = Depends(get_session)
):
    _verein(session, verein_id)
    ergebnis = importieren(await datei.read())
    neu = [Sponsor(verein_id=verein_id, **s.model_dump()) for s in ergebnis.sponsoren]
    session.add_all(neu)
    session.commit()
    for s in neu:
        session.refresh(s)
    return ImportAntwort(importiert=neu, fehler=ergebnis.fehler)


@router.delete("/sponsoren/{sponsor_id}", status_code=204)
def sponsor_loeschen(sponsor_id: int, session: Session = Depends(get_session)) -> None:
    sponsor = session.get(Sponsor, sponsor_id)
    if not sponsor:
        raise HTTPException(404, "Sponsor nicht gefunden")
    session.delete(sponsor)
    session.commit()
