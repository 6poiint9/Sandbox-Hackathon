from fastapi.testclient import TestClient

from app.main import app


def test_health_und_katalog():
    with TestClient(app, headers={"X-Sponsorenkompass": "1"}) as client:
        antwort = client.get("/health")
        assert antwort.status_code == 200
        assert antwort.json()["katalog_eintraege"] == 26

        katalog = client.get("/katalog").json()
        ids = {e["id"] for e in katalog}
        assert {"bande", "trikot_brust", "azubi"} <= ids
