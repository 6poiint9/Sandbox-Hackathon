"""Anmeldung und Zugriffsschutz – echte Cookies über HTTPS, ohne Test-Override."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db import get_session
from app.main import app
from app.models import Kandidat, Konto, Sitzung, Unternehmen
from app.services import auth
from app.services.auth import aktuelles_konto, cookie_name

CSRF = {"X-Sponsorenkompass": "1"}
PW = "lange-sichere-" + "testphrase-7"  # Testwert, nur hier verwendet
PW2 = "andere-lange-" + "testphrase-9"


@pytest.fixture
def umgebung():
    app.dependency_overrides.pop(aktuelles_konto, None)  # echte Anmeldung prüfen
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)

    def override():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield eng
    app.dependency_overrides.clear()


def neuer_client(**kw) -> TestClient:
    return TestClient(app, base_url="https://testserver", headers=CSRF, **kw)


def registrieren(c: TestClient, email: str, pw: str = PW):
    return c.post("/konto/registrieren", json={"email": email, "passwort": pw})


def test_ohne_anmeldung_ist_alles_zu(umgebung):
    with neuer_client() as c:
        assert c.post("/onboarding/analyse", json={"website": "x.de"}).status_code == 401
        assert c.post("/vereine", json={"name": "FC", "ort": "O"}).status_code == 401
        assert c.get("/vereine/1").status_code == 401
        assert c.get("/kandidaten/1/ansprache").status_code == 401
        assert c.get("/health").status_code == 200  # öffentlich
        assert c.get("/interessenten/anzahl").status_code == 200


def test_cookie_ist_httponly_secure_strict_und_token_nur_gehasht(umgebung):
    with neuer_client() as c:
        r = registrieren(c, "kasse@fc.example")
        assert r.status_code == 200, r.text
        kopf = r.headers["set-cookie"]
        assert cookie_name() in kopf and "HttpOnly" in kopf and "Secure" in kopf and "SameSite=strict" in kopf
        assert "token" not in r.json()  # kein Token im Body/JS
        token = c.cookies.get(cookie_name())
        with Session(umgebung) as s:
            gespeichert = s.exec(select(Sitzung)).one()
            assert gespeichert.token_hash != token and len(gespeichert.token_hash) == 64
            konto = s.exec(select(Konto)).one()
            assert konto.passwort_hash.startswith("$argon2id$")
        assert c.get("/konto/ich").json()["email"] == "kasse@fc.example"


def test_passwortregeln(umgebung, monkeypatch):
    with neuer_client() as c:
        assert registrieren(c, "a@fc.example", "zu-kurz").status_code == 422
        assert registrieren(c, "a@fc.example", "passwort1234").status_code == 422  # häufig
        assert registrieren(c, "kassenwart@fc.example", "kassenwart-2026-x").status_code == 422  # E-Mail darin
        monkeypatch.setattr(auth, "in_datenleck", lambda pw: True)
        r = registrieren(c, "a@fc.example")
        assert r.status_code == 422 and "Datenleck" in r.json()["detail"]


def test_leckpruefung_sendet_nur_hashanfang(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "passwort_leckpruefung", True)
    gesehen = []

    def fake_get(url, **kw):
        gesehen.append(url)
        # SHA-1("password") = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
        return SimpleNamespace(text="1E4C9B93F3F0682250B6CF8331B7EE68FD8:9545824\r\nABC:0", raise_for_status=lambda: None)

    monkeypatch.setattr(auth.httpx, "get", fake_get)
    assert auth.in_datenleck("password") is True
    assert gesehen == ["https://api.pwnedpasswords.com/range/5BAA6"]
    assert auth.in_datenleck("etwas-ganz-anderes-123") is False


def test_anmelden_einheitliche_fehler_und_begrenzung(umgebung):
    with neuer_client() as c:
        registrieren(c, "kasse@fc.example")
    with neuer_client() as c:
        falsch = c.post("/konto/anmelden", json={"email": "kasse@fc.example", "passwort": "falsch-falsch-1"})
        unbekannt = c.post("/konto/anmelden", json={"email": "gibts@nicht.example", "passwort": "falsch-falsch-1"})
        assert falsch.status_code == unbekannt.status_code == 401
        assert falsch.json() == unbekannt.json()  # verrät nicht, ob es das Konto gibt
        for _ in range(4):
            c.post("/konto/anmelden", json={"email": "kasse@fc.example", "passwort": "falsch-falsch-1"})
        gesperrt = c.post("/konto/anmelden", json={"email": "kasse@fc.example", "passwort": PW})
        assert gesperrt.status_code == 429 and "Retry-After" in gesperrt.headers


def test_csrf_ohne_header_oder_fremder_origin_abgelehnt(umgebung):
    with TestClient(app, base_url="https://testserver") as c:
        assert c.post("/konto/registrieren", json={"email": "a@fc.example", "passwort": PW}).status_code == 403
    with neuer_client() as c:
        r = c.post("/konto/registrieren", json={"email": "a@fc.example", "passwort": PW},
                   headers={"Origin": "https://boese.example"})
        assert r.status_code == 403


def test_fremde_objekte_sind_404(umgebung):
    with neuer_client() as a:
        registrieren(a, "a@fc.example")
        vid = a.post("/vereine", json={"name": "FC A", "ort": "O"}).json()["id"]
        sid = a.post(f"/vereine/{vid}/sponsoren", json=[{"firma": "Bäckerei"}]).json()[0]["id"]
        with Session(umgebung) as s:
            s.add(Unternehmen(id=1, osm_id="n/1", name="U", branche="Handel", lat=0, lon=0))
            s.add(Kandidat(id=1, verein_id=vid, unternehmen_id=1, entfernung_km=1, vorfilter_score=1))
            s.commit()
        assert a.get(f"/vereine/{vid}/sponsoren").status_code == 200
    with neuer_client() as b:
        registrieren(b, "b@fc.example", PW2)
        assert b.get(f"/vereine/{vid}").status_code == 404
        assert b.patch(f"/sponsoren/{sid}", json={"betrag_eur": 1}).status_code == 404
        assert b.patch("/kandidaten/1", json={"notiz": "x"}).status_code == 404
        assert b.post(f"/kandidaten/1/zum-sponsor", json={}).status_code == 404
        # eigener Verein, aber fremder Sponsor im Body
        eigen = b.post("/vereine", json={"name": "FC B", "ort": "O"}).json()["id"]
        r = b.post(f"/vereine/{eigen}/aktivitaeten", json={"text": "x", "sponsor_id": sid})
        assert r.status_code == 404
        assert {v["id"] for v in b.get("/konto/vereine").json()} == {eigen}


def test_abmelden_ablauf_und_passwortwechsel(umgebung):
    with neuer_client() as c:
        registrieren(c, "kasse@fc.example")
        c.post("/konto/abmelden")
        assert c.get("/konto/ich").status_code == 401
        assert c.post("/konto/anmelden", json={"email": "kasse@fc.example", "passwort": PW}).status_code == 200
        # abgelaufene Sitzung gilt nicht mehr
        with Session(umgebung) as s:
            for sitz in s.exec(select(Sitzung)).all():
                sitz.ablauf = datetime.now(timezone.utc) - timedelta(minutes=1)
                s.add(sitz)
            s.commit()
        assert c.get("/konto/ich").status_code == 401
        c.post("/konto/anmelden", json={"email": "kasse@fc.example", "passwort": PW})
        with neuer_client() as zweites_geraet:
            zweites_geraet.post("/konto/anmelden", json={"email": "kasse@fc.example", "passwort": PW})
            assert c.post("/konto/passwort", json={"altes_passwort": PW, "neues_passwort": PW2}).status_code == 200
            assert zweites_geraet.get("/konto/ich").status_code == 401  # andere Geräte abgemeldet
        assert c.get("/konto/ich").status_code == 200  # dieses Gerät bleibt angemeldet
