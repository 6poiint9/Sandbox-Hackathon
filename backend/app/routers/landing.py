"""Landingpage: Anmeldungen für Warteliste und Pilotvereine."""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.db import get_session
from app.models import Interessent

router = APIRouter(tags=["landing"])
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Anmeldung(BaseModel):
    email: str
    verein: str | None = None
    rolle: str | None = None
    nachricht: str | None = None
    pilot: bool = False


class Zaehler(BaseModel):
    anmeldungen: int
    pilotvereine: int


@router.post("/interessenten", response_model=Zaehler)
def anmelden(daten: Anmeldung, session: Session = Depends(get_session)) -> Zaehler:
    email = daten.email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(422, "Bitte eine gültige E-Mail-Adresse eintragen")
    vorhanden = session.exec(select(Interessent).where(Interessent.email == email)).first()
    if vorhanden:  # doppelte Anmeldung aktualisiert statt zu verdoppeln
        for feld, wert in daten.model_dump(exclude={"email"}, exclude_none=True).items():
            setattr(vorhanden, feld, wert)
        session.add(vorhanden)
    else:
        session.add(Interessent(**daten.model_dump(exclude={"email"}), email=email))
    session.commit()
    return zaehler(session)


@router.get("/interessenten/anzahl", response_model=Zaehler)
def zaehler(session: Session = Depends(get_session)) -> Zaehler:
    gesamt = session.exec(select(func.count()).select_from(Interessent)).one()
    pilot = session.exec(select(func.count()).select_from(Interessent).where(Interessent.pilot)).one()
    return Zaehler(anmeldungen=gesamt, pilotvereine=pilot)
