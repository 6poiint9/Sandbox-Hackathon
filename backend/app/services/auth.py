"""Anmeldung nach aktuellem Stand (OWASP ASVS / NIST SP 800-63B).

- Passwörter: Argon2id (m=64 MiB, t=3, p=4), automatische Neuberechnung bei
  veralteten Parametern oder altem scrypt-Hash.
- Passwortregeln: mind. 12 Zeichen, nicht E-Mail-Bestandteil, nicht in Liste
  häufiger Passwörter, nicht in bekannten Datenlecks (Have I Been Pwned,
  k-Anonymität: nur die ersten 5 Zeichen des SHA-1 verlassen den Server).
- Sitzung: zufälliges Token (256 Bit) nur im HttpOnly-, Secure-, SameSite=Strict-
  Cookie; in der DB nur sein SHA-256. Absolute Laufzeit und Leerlauf-Ablauf,
  neue Sitzung bei jeder Anmeldung, Abmelden überall.
- Brute-Force: Begrenzung je E-Mail und je IP, gleiche Antwortzeit bei
  unbekannter E-Mail (Dummy-Hash), einheitliche Fehlermeldung.
- CSRF: zustandsändernde Anfragen brauchen den Header X-Sponsorenkompass und
  ggf. einen erlaubten Origin (siehe main.py).
- Zugriff: Jedes Objekt (Verein, Kandidat, Sponsor, Asset, …) nur für das
  Konto, dem der Verein gehört. Fremdes wird als 404 gemeldet.
"""

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.models import Konto, Sitzung

PH = PasswordHasher()  # Argon2id, Standardparameter entsprechen den OWASP-Empfehlungen
_DUMMY = PH.hash("dummy-passwort-fuer-gleiche-laufzeit")
CSRF_HEADER = "X-Sponsorenkompass"

HAEUFIGE = {
    "passwort1234", "passwort12345", "123456789012", "qwertzuiop12", "hallo1234567",
    "fussball1234", "sponsoren123", "verein123456", "password1234", "letmein12345",
    "1234567890ab", "abcdefghijkl", "willkommen12", "sommer202612", "geheim123456",
}


def cookie_name() -> str:
    # __Host- erzwingt Secure, Pfad / und keine Domain – Schutz vor Subdomain-Überschreiben
    return "__Host-sk_sitzung" if get_settings().cookie_secure else "sk_sitzung"


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _utc(d: datetime | None) -> datetime | None:
    return d.replace(tzinfo=timezone.utc) if d and d.tzinfo is None else d


# --- Passwörter -------------------------------------------------------------


def passwort_hashen(passwort: str) -> str:
    return PH.hash(passwort)


def _scrypt_alt(passwort: str, gespeichert: str) -> bool:
    try:
        _, salz, h = gespeichert.split("$")
        neu = hashlib.scrypt(passwort.encode(), salt=bytes.fromhex(salz), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(neu.hex(), h)
    except ValueError:
        return False


def passwort_pruefen(passwort: str, gespeichert: str | None) -> bool:
    if not gespeichert:
        try:
            PH.verify(_DUMMY, passwort)  # gleiche Laufzeit wie bei existierendem Konto
        except VerificationError:
            pass
        return False
    if gespeichert.startswith("scrypt$"):
        return _scrypt_alt(passwort, gespeichert)
    try:
        return PH.verify(gespeichert, passwort)
    except (VerificationError, InvalidHashError):
        return False


def braucht_neuen_hash(gespeichert: str) -> bool:
    return gespeichert.startswith("scrypt$") or PH.check_needs_rehash(gespeichert)


def in_datenleck(passwort: str) -> bool:
    """Have I Been Pwned, k-Anonymität. Bei Netzfehlern: nicht blockieren."""
    if not get_settings().passwort_leckpruefung:
        return False
    sha1 = hashlib.sha1(passwort.encode()).hexdigest().upper()
    try:
        r = httpx.get(f"https://api.pwnedpasswords.com/range/{sha1[:5]}", headers={"Add-Padding": "true"}, timeout=4)
        r.raise_for_status()
    except httpx.HTTPError:
        return False
    for zeile in r.text.splitlines():
        rest, _, anzahl = zeile.partition(":")
        if rest.strip() == sha1[5:] and anzahl.strip() not in ("", "0"):
            return True
    return False


def passwort_regeln(passwort: str, email: str) -> None:
    if len(passwort) < 12:
        raise HTTPException(422, "Das Passwort braucht mindestens 12 Zeichen.")
    if len(passwort) > 256:
        raise HTTPException(422, "Das Passwort ist zu lang (höchstens 256 Zeichen).")
    klein = passwort.lower()
    lokal = email.split("@")[0].lower()
    if klein in HAEUFIGE or len(set(klein)) < 4 or (len(lokal) >= 4 and lokal in klein):
        raise HTTPException(422, "Dieses Passwort ist zu leicht zu erraten. Tipp: mehrere Wörter kombinieren.")
    if in_datenleck(passwort):
        raise HTTPException(422, "Dieses Passwort ist aus Datenlecks bekannt. Bitte ein anderes wählen.")


# --- Begrenzung von Versuchen -----------------------------------------------


class Begrenzer:
    """Gleitendes Fenster im Speicher (eine Instanz; für mehrere Server: Redis o. Ä.)."""

    def __init__(self) -> None:
        self._eintraege: dict[str, deque[float]] = defaultdict(deque)
        self._sperre = threading.Lock()

    def pruefen(self, schluessel: str, max_anzahl: int, fenster_s: int) -> None:
        jetzt = time.monotonic()
        with self._sperre:
            q = self._eintraege[schluessel]
            while q and jetzt - q[0] > fenster_s:
                q.popleft()
            if len(q) >= max_anzahl:
                warten = int(fenster_s - (jetzt - q[0])) + 1
                raise HTTPException(429, "Zu viele Versuche. Bitte später erneut probieren.",
                                    headers={"Retry-After": str(warten)})
            q.append(jetzt)

    def zuruecksetzen(self, schluessel: str) -> None:
        with self._sperre:
            self._eintraege.pop(schluessel, None)

    def leeren(self) -> None:
        with self._sperre:
            self._eintraege.clear()


BEGRENZER = Begrenzer()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unbekannt"


# --- Sitzungen --------------------------------------------------------------


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def sitzung_starten(session: Session, response: Response, konto_id: int) -> None:
    s = get_settings()
    token = secrets.token_urlsafe(32)
    jetzt = _jetzt()
    ablauf = jetzt + timedelta(days=s.sitzung_tage)
    session.add(Sitzung(token_hash=_token_hash(token), konto_id=konto_id, erstellt=jetzt,
                        ablauf=ablauf, letzter_zugriff=jetzt))
    session.commit()
    response.set_cookie(
        cookie_name(), token, max_age=s.sitzung_tage * 86400, path="/",
        httponly=True, secure=s.cookie_secure, samesite="strict",
    )


def sitzung_beenden(session: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(cookie_name())
    if token:
        alt = session.get(Sitzung, _token_hash(token))
        if alt:
            session.delete(alt)
            session.commit()
    response.delete_cookie(cookie_name(), path="/", secure=get_settings().cookie_secure,
                           httponly=True, samesite="strict")


def alle_sitzungen_beenden(session: Session, konto_id: int) -> None:
    for s in session.exec(select(Sitzung).where(Sitzung.konto_id == konto_id)).all():
        session.delete(s)
    session.commit()


def optionales_konto(request: Request, session: Session = Depends(get_session)) -> Konto | None:
    token = request.cookies.get(cookie_name())
    if not token:
        return None
    s = session.get(Sitzung, _token_hash(token))
    if not s:
        return None
    jetzt = _jetzt()
    leerlauf = timedelta(hours=get_settings().sitzung_leerlauf_stunden)
    if (s.ablauf and _utc(s.ablauf) < jetzt) or (s.letzter_zugriff and _utc(s.letzter_zugriff) + leerlauf < jetzt):
        session.delete(s)
        session.commit()
        return None
    if not s.letzter_zugriff or jetzt - _utc(s.letzter_zugriff) > timedelta(minutes=5):
        s.letzter_zugriff = jetzt
        session.add(s)
        session.commit()
    return session.get(Konto, s.konto_id)


def aktuelles_konto(konto: Konto | None = Depends(optionales_konto)) -> Konto:
    if not konto:
        raise HTTPException(401, "Bitte anmelden.")
    return konto


# --- Besitz prüfen ----------------------------------------------------------


def verein_von(session: Session, art: str, id_: int) -> int | None:
    """Zu welchem Verein gehört ein Objekt? None, wenn es nicht existiert."""
    from app.models import Aktivitaet, AssetVergabe, InventarPosten, Kandidat, Sponsor, Verein

    if art == "verein_id":
        return id_ if session.get(Verein, id_) else None
    modell = {"kandidat_id": Kandidat, "sponsor_id": Sponsor, "asset_id": InventarPosten, "aktivitaet_id": Aktivitaet}.get(art)
    if modell:
        obj = session.get(modell, id_)
        return obj.verein_id if obj else None
    if art == "vergabe_id":
        v = session.get(AssetVergabe, id_)
        a = session.get(InventarPosten, v.asset_id) if v else None
        return a.verein_id if a else None
    return None


# --- Gäste ohne Konto -------------------------------------------------------
# "Kostenlos ausprobieren" ohne Anmeldung: Der Browser bekommt ein zufälliges
# Gast-Token (256 Bit) im HttpOnly-/SameSite=Strict-Cookie; am Verein liegt nur
# sein SHA-256. Bei Registrierung oder Anmeldung wandern die Vereine ins Konto.

GAST_TAGE = 30


def gast_cookie_name() -> str:
    return "__Host-sk_gast" if get_settings().cookie_secure else "sk_gast"


@dataclass(frozen=True)
class Inhaber:
    """Wer fragt: ein angemeldetes Konto oder ein Gast (nie beides)."""

    konto: Konto | None
    gast_hash: str | None

    @property
    def abo(self) -> bool:
        return bool(self.konto and self.konto.abo)


def inhaber(request: Request, response: Response, konto: Konto | None = Depends(optionales_konto)) -> Inhaber:
    """Konto, sonst Gast. Ohne gültiges Gast-Cookie wird ein neues ausgestellt."""
    if konto:
        return Inhaber(konto=konto, gast_hash=None)
    token = request.cookies.get(gast_cookie_name())
    if not token or not 20 <= len(token) <= 100:
        token = secrets.token_urlsafe(32)
        response.set_cookie(
            gast_cookie_name(), token, max_age=GAST_TAGE * 86400, path="/",
            httponly=True, secure=get_settings().cookie_secure, samesite="strict",
        )
    return Inhaber(konto=None, gast_hash=_token_hash(token))


def gast_uebernehmen(session: Session, request: Request, response: Response, konto_id: int) -> int:
    """Nach Registrierung/Anmeldung: Vereine des Gast-Cookies gehören jetzt dem Konto."""
    from app.models import Verein

    token = request.cookies.get(gast_cookie_name())
    if not token:
        return 0
    vereine = session.exec(
        select(Verein).where(Verein.gast_hash == _token_hash(token), Verein.konto_id.is_(None))
    ).all()
    for v in vereine:
        v.konto_id = konto_id
        v.gast_hash = None
        session.add(v)
    session.commit()
    response.delete_cookie(gast_cookie_name(), path="/", secure=get_settings().cookie_secure,
                           httponly=True, samesite="strict")
    return len(vereine)


def besitzt(wer: Inhaber, verein) -> bool:
    if wer.konto:
        return verein.konto_id == wer.konto.id
    return (
        verein.konto_id is None
        and bool(verein.gast_hash and wer.gast_hash)
        and hmac.compare_digest(verein.gast_hash, wer.gast_hash)
    )


def gehoert(session: Session, wer: Inhaber, art: str, id_: int | None) -> None:
    """404 statt 403: fremde Objekte sollen nicht einmal ihre Existenz verraten."""
    from app.models import Verein

    if id_ is None:
        return
    vid = verein_von(session, art, id_)
    verein = session.get(Verein, vid) if vid else None
    if not verein or not besitzt(wer, verein):
        raise HTTPException(404, "Nicht gefunden")


def gehoert_konto(session: Session, konto: Konto, art: str, id_: int | None) -> None:
    gehoert(session, Inhaber(konto=konto, gast_hash=None), art, id_)


PFAD_IDS = ("verein_id", "kandidat_id", "sponsor_id", "asset_id", "vergabe_id", "aktivitaet_id")


def zugriff(request: Request, wer: Inhaber = Depends(inhaber), session: Session = Depends(get_session)) -> Inhaber:
    """Für alle geschützten Router: Besitzer aller IDs im Pfad (Konto oder Gast).

    Gesperrte Kandidaten (ohne Abo nicht unter den freien) melden 402.
    """
    from app.services import freigabe

    for art in PFAD_IDS:
        roh = request.path_params.get(art)
        if roh is not None:
            gehoert(session, wer, art, int(roh))
    roh = request.path_params.get("kandidat_id")
    if roh is not None and not wer.abo:
        freigabe.pruefen(session, int(roh))
    return wer
