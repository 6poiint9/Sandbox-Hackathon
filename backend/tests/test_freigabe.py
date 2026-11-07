"""Gastzugang und Freemium-Sperre – echte Cookies, ohne Test-Override."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import Kandidat, Unternehmen
from app.services import auth
from app.services.auth import aktuelles_konto, inhaber

CSRF = {"X-Sponsorenkompass": "1"}
PW = "gast-wird-" + "kassenwart-2026"


@pytest.fixture
def umgebung():
    app.dependency_overrides.pop(aktuelles_konto, None)
    app.dependency_overrides.pop(inhaber, None)
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)

    def override():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield eng
    app.dependency_overrides.clear()


def client() -> TestClient:
    return TestClient(app, base_url="https://testserver", headers=CSRF)


def fuenf_kandidaten(eng, verein_id: int) -> None:
    """Vorfilter-Score 90, 80, 70, 60, 50: frei sind die ersten drei (IDs 1–3)."""
    with Session(eng) as s:
        for i in range(1, 6):
            s.add(Unternehmen(id=i, osm_id=f"n/{i}", name=f"Betrieb {i} GmbH", branche="Handwerk",
                              adresse=f"Weg {i}", lat=47.99123 + i / 1000, lon=7.84567, website=f"https://b{i}.example"))
            s.add(Kandidat(id=i, verein_id=verein_id, unternehmen_id=i, entfernung_km=i * 1.234,
                           vorfilter_score=100 - i * 10, recherche_status="fertig", score=60 + i,
                           gruende=[{"text": f"Grund {i}", "quelle_url": f"https://q{i}.example"}],
                           paket_empfehlung={"katalog_ids": ["bande"]}, notiz=f"geheim {i}"))
        s.commit()


def test_gast_sieht_drei_frei_und_den_rest_geschwaerzt(umgebung):
    with client() as gast:
        vid = gast.post("/vereine", json={"name": "FC Gast", "ort": "O", "ziel_eur": 50000}).json()["id"]
        fuenf_kandidaten(umgebung, vid)

        liste = gast.get(f"/vereine/{vid}/kandidaten").json()
        frei = [k for k in liste if not k["gesperrt"]]
        gesperrt = [k for k in liste if k["gesperrt"]]
        assert [k["id"] for k in frei] == [3, 2, 1] or sorted(k["id"] for k in frei) == [1, 2, 3]
        assert sorted(k["id"] for k in gesperrt) == [4, 5]
        assert liste[:3] == frei  # freie stehen vorn
        for k in gesperrt:
            u = k["unternehmen"]
            assert u["name"] == "Gesperrter Betrieb" and u["website"] is None and u["adresse"] is None
            assert u["branche"] == "Handwerk" and k["gruende"] == [] and k["score"] is None
            assert u["lat"] == round(u["lat"], 2)  # nur grob verortet
        roh = gast.get(f"/vereine/{vid}/kandidaten").text
        for verraeterisch in ("Betrieb 4", "Betrieb 5", "b4.example", "Weg 5", "geheim 4", "Grund 5", "q4.example"):
            assert verraeterisch not in roh

        assert gast.get("/kandidaten/4/ansprache").status_code == 402
        assert gast.patch("/kandidaten/5/status", json={"status": "kontaktiert"}).status_code == 402
        assert gast.get("/kandidaten/1/ansprache").status_code == 404  # frei, nur noch keine Ansprache
        assert gast.get(f"/vereine/{vid}/export").status_code == 402

        plan = gast.get(f"/vereine/{vid}/plan").json()
        namen = [c["name"] for z in plan["zeilen"] for c in z["kandidaten"]]
        assert not any(n in ("Betrieb 4 GmbH", "Betrieb 5 GmbH") for n in namen)

    with client() as anderer_gast:
        assert anderer_gast.get(f"/vereine/{vid}").status_code == 404
        assert anderer_gast.get(f"/vereine/{vid}/kandidaten").status_code == 404


def test_registrieren_uebernimmt_verein_und_abo_schaltet_alles_frei(umgebung):
    with client() as c:
        vid = c.post("/vereine", json={"name": "FC Gast", "ort": "O"}).json()["id"]
        fuenf_kandidaten(umgebung, vid)
        assert auth.gast_cookie_name() in c.cookies

        r = c.post("/konto/registrieren", json={"email": "info@fc.example", "passwort": PW})
        assert r.status_code == 200 and r.json()["abo"] is False
        assert [v["id"] for v in c.get("/konto/vereine").json()] == [vid]  # Verein ist jetzt im Konto
        assert auth.gast_cookie_name() not in c.cookies  # Gast-Cookie gelöscht
        assert c.get("/kandidaten/4/ansprache").status_code == 402  # Konto allein reicht nicht

        assert c.post("/konto/abo", json={"aktiv": True}).json()["abo"] is True
        liste = c.get(f"/vereine/{vid}/kandidaten").json()
        assert not any(k["gesperrt"] for k in liste)
        assert {k["unternehmen"]["name"] for k in liste} >= {"Betrieb 4 GmbH", "Betrieb 5 GmbH"}
        assert c.get("/kandidaten/4/ansprache").status_code == 404  # freigeschaltet, nur keine Ansprache
        assert c.get(f"/vereine/{vid}/export").status_code == 200

    with client() as gast:
        assert gast.get(f"/vereine/{vid}").status_code == 404  # ehemaliger Gastverein bleibt privat
        assert gast.post("/konto/abo", json={"aktiv": True}).status_code == 401
