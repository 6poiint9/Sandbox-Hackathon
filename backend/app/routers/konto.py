"""Registrierung, Anmeldung, eigene Vereine."""

import re

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Konto, Sitzung, Verein
from app.services.auth import (
    konto_pflicht,
    passwort_hashen,
    passwort_pruefen,
    sitzung_anlegen,
    token_hash,
)

router = APIRouter(prefix="/konto", tags=["konto"])
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class KontoAnsicht(BaseModel):
    id: int
    email: str
    name: str | None


class Anmeldung(BaseModel):
    email: str
    passwort: str
    name: str | None = None


class AnmeldeAntwort(BaseModel):
    token: str
    konto: KontoAnsicht


def _ansicht(k: Konto) -> KontoAnsicht:
    return KontoAnsicht(id=k.id, email=k.email, name=k.name)


@router.post("/registrieren", response_model=AnmeldeAntwort)
def registrieren(daten: Anmeldung, session: Session = Depends(get_session)):
    email = daten.email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(422, "Bitte eine gültige E-Mail-Adresse eintragen")
    if len(daten.passwort) < 8:
        raise HTTPException(422, "Das Passwort braucht mindestens 8 Zeichen")
    if session.exec(select(Konto).where(Konto.email == email)).first():
        raise HTTPException(409, "Für diese E-Mail gibt es schon ein Konto – bitte anmelden")
    k = Konto(email=email, name=(daten.name or "").strip() or None, passwort_hash=passwort_hashen(daten.passwort))
    session.add(k)
    session.commit()
    session.refresh(k)
    return AnmeldeAntwort(token=sitzung_anlegen(session, k.id), konto=_ansicht(k))


@router.post("/anmelden", response_model=AnmeldeAntwort)
def anmelden(daten: Anmeldung, session: Session = Depends(get_session)):
    k = session.exec(select(Konto).where(Konto.email == daten.email.strip().lower())).first()
    if not k or not passwort_pruefen(daten.passwort, k.passwort_hash):
        raise HTTPException(401, "E-Mail oder Passwort stimmt nicht")
    return AnmeldeAntwort(token=sitzung_anlegen(session, k.id), konto=_ansicht(k))


@router.post("/abmelden", status_code=204)
def abmelden(authorization: str | None = Header(default=None), session: Session = Depends(get_session)) -> None:
    if authorization and authorization.lower().startswith("bearer "):
        s = session.get(Sitzung, token_hash(authorization[7:].strip()))
        if s:
            session.delete(s)
            session.commit()


@router.get("/ich", response_model=KontoAnsicht)
def ich(konto: Konto = Depends(konto_pflicht)):
    return _ansicht(konto)


class VereinKurz(BaseModel):
    id: int
    name: str
    ort: str
    spielklasse: str | None


@router.get("/vereine", response_model=list[VereinKurz])
def meine_vereine(konto: Konto = Depends(konto_pflicht), session: Session = Depends(get_session)):
    vereine = session.exec(select(Verein).where(Verein.konto_id == konto.id)).all()
    return [VereinKurz(id=v.id, name=v.name, ort=v.ort, spielklasse=v.spielklasse) for v in vereine]


@router.post("/vereine/{verein_id}", response_model=list[VereinKurz])
def verein_uebernehmen(verein_id: int, konto: Konto = Depends(konto_pflicht), session: Session = Depends(get_session)):
    """Eine ohne Konto gestartete Analyse ins eigene Konto übernehmen."""
    v = session.get(Verein, verein_id)
    if not v:
        raise HTTPException(404, "Verein nicht gefunden")
    if v.konto_id not in (None, konto.id):
        raise HTTPException(403, "Dieser Verein gehört zu einem anderen Konto")
    v.konto_id = konto.id
    session.add(v)
    session.commit()
    return meine_vereine(konto, session)
