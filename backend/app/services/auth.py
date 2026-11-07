"""Konten: Passwort-Hash (scrypt, stdlib) und Sitzungs-Token."""

import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException, Request
from sqlmodel import Session

from app.db import get_session
from app.models import Konto, Sitzung

SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def passwort_hashen(passwort: str) -> str:
    salz = secrets.token_bytes(16)
    h = hashlib.scrypt(passwort.encode(), salt=salz, **SCRYPT)
    return f"scrypt${salz.hex()}${h.hex()}"


def passwort_pruefen(passwort: str, gespeichert: str) -> bool:
    try:
        _, salz, h = gespeichert.split("$")
    except ValueError:
        return False
    neu = hashlib.scrypt(passwort.encode(), salt=bytes.fromhex(salz), **SCRYPT)
    return hmac.compare_digest(neu.hex(), h)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def sitzung_anlegen(session: Session, konto_id: int) -> str:
    token = secrets.token_urlsafe(32)
    session.add(Sitzung(token_hash=token_hash(token), konto_id=konto_id))
    session.commit()
    return token


def konto_aus_header(authorization: str | None, session: Session) -> Konto | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    s = session.get(Sitzung, token_hash(authorization[7:].strip()))
    return session.get(Konto, s.konto_id) if s else None


def optionales_konto(
    authorization: str | None = Header(default=None), session: Session = Depends(get_session)
) -> Konto | None:
    return konto_aus_header(authorization, session)


def konto_pflicht(konto: Konto | None = Depends(optionales_konto)) -> Konto:
    if not konto:
        raise HTTPException(401, "Bitte anmelden")
    return konto


def vereinszugriff(
    request: Request,
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> None:
    """Gilt für alle Pfade mit {verein_id}: Gehört der Verein einem Konto, nur mit dessen Anmeldung."""
    roh = request.path_params.get("verein_id")
    if roh is None:
        return
    from app.models import Verein

    v = session.get(Verein, int(roh))
    if not v or v.konto_id is None:
        return
    konto = konto_aus_header(authorization, session)
    if not konto:
        raise HTTPException(401, "Bitte anmelden – dieser Verein gehört zu einem Konto")
    if konto.id != v.konto_id:
        raise HTTPException(403, "Kein Zugriff auf diesen Verein")
