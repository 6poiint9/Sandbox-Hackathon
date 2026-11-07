"""Registrierung, Anmeldung, Sitzungen, Passwort ändern, eigene Vereine."""

import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Konto, Verein
from app.services.auth import (
    BEGRENZER,
    aktuelles_konto,
    alle_sitzungen_beenden,
    braucht_neuen_hash,
    client_ip,
    gast_uebernehmen,
    passwort_hashen,
    passwort_pruefen,
    passwort_regeln,
    sitzung_beenden,
    sitzung_starten,
)

router = APIRouter(prefix="/konto", tags=["konto"])
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
FALSCH = "E-Mail oder Passwort stimmt nicht."


class KontoAnsicht(BaseModel):
    id: int
    email: str
    name: str | None
    abo: bool = False


class AboWunsch(BaseModel):
    aktiv: bool


class Registrierung(BaseModel):
    email: str
    passwort: str
    name: str | None = None


class Login(BaseModel):
    email: str
    passwort: str


class PasswortWechsel(BaseModel):
    altes_passwort: str
    neues_passwort: str


def _ansicht(k: Konto) -> KontoAnsicht:
    return KontoAnsicht(id=k.id, email=k.email, name=k.name, abo=k.abo)


@router.post("/registrieren", response_model=KontoAnsicht)
def registrieren(daten: Registrierung, request: Request, response: Response, session: Session = Depends(get_session)):
    BEGRENZER.pruefen(f"reg:{client_ip(request)}", 5, 3600)
    email = daten.email.strip().lower()
    if not EMAIL.match(email) or len(email) > 254:
        raise HTTPException(422, "Bitte eine gültige E-Mail-Adresse eintragen.")
    passwort_regeln(daten.passwort, email)
    if session.exec(select(Konto).where(Konto.email == email)).first():
        raise HTTPException(409, "Mit dieser E-Mail ist keine Registrierung möglich. Schon ein Konto? Bitte anmelden.")
    k = Konto(email=email, name=(daten.name or "").strip()[:100] or None, passwort_hash=passwort_hashen(daten.passwort))
    session.add(k)
    session.commit()
    session.refresh(k)
    sitzung_starten(session, response, k.id)
    gast_uebernehmen(session, request, response, k.id)
    return _ansicht(k)


@router.post("/anmelden", response_model=KontoAnsicht)
def anmelden(daten: Login, request: Request, response: Response, session: Session = Depends(get_session)):
    email = daten.email.strip().lower()
    BEGRENZER.pruefen(f"login-ip:{client_ip(request)}", 20, 900)
    BEGRENZER.pruefen(f"login-mail:{email}", 5, 900)
    k = session.exec(select(Konto).where(Konto.email == email)).first()
    if not passwort_pruefen(daten.passwort, k.passwort_hash if k else None) or not k:
        raise HTTPException(401, FALSCH)
    BEGRENZER.zuruecksetzen(f"login-mail:{email}")
    if braucht_neuen_hash(k.passwort_hash):
        k.passwort_hash = passwort_hashen(daten.passwort)
        session.add(k)
        session.commit()
    sitzung_starten(session, response, k.id)  # immer neue Sitzung (kein Session Fixation)
    gast_uebernehmen(session, request, response, k.id)
    return _ansicht(k)


@router.post("/abmelden", status_code=204)
def abmelden(request: Request, response: Response, session: Session = Depends(get_session)) -> None:
    sitzung_beenden(session, request, response)


@router.post("/ueberall-abmelden", status_code=204)
def ueberall_abmelden(request: Request, response: Response, konto: Konto = Depends(aktuelles_konto),
                      session: Session = Depends(get_session)) -> None:
    alle_sitzungen_beenden(session, konto.id)
    sitzung_beenden(session, request, response)


@router.post("/passwort", response_model=KontoAnsicht)
def passwort_aendern(daten: PasswortWechsel, request: Request, response: Response,
                     konto: Konto = Depends(aktuelles_konto), session: Session = Depends(get_session)):
    BEGRENZER.pruefen(f"pw:{konto.id}", 5, 900)
    if not passwort_pruefen(daten.altes_passwort, konto.passwort_hash):
        raise HTTPException(401, "Das bisherige Passwort stimmt nicht.")
    passwort_regeln(daten.neues_passwort, konto.email)
    konto.passwort_hash = passwort_hashen(daten.neues_passwort)
    session.add(konto)
    session.commit()
    alle_sitzungen_beenden(session, konto.id)  # alle anderen Geräte abmelden
    sitzung_starten(session, response, konto.id)
    return _ansicht(konto)


@router.get("/ich", response_model=KontoAnsicht)
def ich(response: Response, konto: Konto = Depends(aktuelles_konto)):
    response.headers["Cache-Control"] = "no-store"
    return _ansicht(konto)


@router.post("/abo", response_model=KontoAnsicht)
def abo_setzen(daten: AboWunsch, konto: Konto = Depends(aktuelles_konto), session: Session = Depends(get_session)):
    """Demo-Abo: schaltet alle Kandidaten frei. Keine Zahlung (README: Bezahlung bewusst nicht im MVP)."""
    konto.abo = daten.aktiv
    session.add(konto)
    session.commit()
    session.refresh(konto)
    return _ansicht(konto)


class VereinKurz(BaseModel):
    id: int
    name: str
    ort: str
    spielklasse: str | None


@router.get("/vereine", response_model=list[VereinKurz])
def meine_vereine(konto: Konto = Depends(aktuelles_konto), session: Session = Depends(get_session)):
    vereine = session.exec(select(Verein).where(Verein.konto_id == konto.id)).all()
    return [VereinKurz(id=v.id, name=v.name, ort=v.ort, spielklasse=v.spielklasse) for v in vereine]
