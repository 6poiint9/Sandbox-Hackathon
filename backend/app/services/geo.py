"""Geokodierung (Nominatim) und Entfernung.

Nominatim-Regeln: eigener User-Agent, höchstens 1 Anfrage pro Sekunde,
Ergebnisse cachen.
"""

import math
import threading
import time

import httpx

from app.providers.cache import zwischengespeichert

USER_AGENT = "Sponsorenkompass/0.1 (Hackathon-Prototyp)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

_sperre = threading.Lock()
_letzte_anfrage = 0.0


class GeoFehler(RuntimeError):
    pass


def _drosseln() -> None:
    global _letzte_anfrage
    with _sperre:
        warten = 1.0 - (time.monotonic() - _letzte_anfrage)
        if warten > 0:
            time.sleep(warten)
        _letzte_anfrage = time.monotonic()


def geokodieren(ort: str) -> tuple[float, float]:
    def holen() -> dict:
        _drosseln()
        antwort = httpx.get(
            NOMINATIM_URL,
            params={"q": ort, "format": "jsonv2", "limit": 1, "countrycodes": "de"},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        antwort.raise_for_status()
        treffer = antwort.json()
        if not treffer:
            raise GeoFehler(f"Ort nicht gefunden: {ort}")
        return {"lat": float(treffer[0]["lat"]), "lon": float(treffer[0]["lon"])}

    try:
        ergebnis = zwischengespeichert("nominatim", holen, ort=ort.strip().lower())
    except httpx.HTTPError as e:
        raise GeoFehler(f"Geokodierung fehlgeschlagen: {e}") from e
    return ergebnis["lat"], ergebnis["lon"]


def entfernung_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
