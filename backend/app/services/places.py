"""Betriebe im Umkreis über die Google Places API (New), Nearby Search.

Schnell (< 2 s für alle Branchen, parallel) und zuverlässig – im Gegensatz zu den
öffentlichen Overpass-Servern, die am 07.11.2026 regelmäßig überlastet waren.
Anmeldung über den Google-Login (ADC) des Projekts, wie bei Gemini/Vertex.

Hinweis Nutzungsbedingungen: Google-Places-Inhalte dürfen nur begrenzt
zwischengespeichert werden. Für den Produktivbetrieb prüfen (place_id dauerhaft ok).
"""

import re
from concurrent.futures import ThreadPoolExecutor

import httpx

from app.config import get_settings
from app.providers.cache import zwischengespeichert
from app.services.geo import entfernung_km
from app.services.osm import Betrieb, OsmFehler

URL = "https://places.googleapis.com/v1/places:searchNearby"
FELDER = "places.id,places.displayName,places.primaryType,places.types,places.websiteUri,places.formattedAddress,places.location"

# Unsere Branche -> Google-Ortstypen (Tabelle A). Je Abfrage höchstens 20 Treffer,
# sortiert nach Beliebtheit – größere, bekannte Betriebe zuerst.
BRANCHEN_TYPEN: dict[str, list[str]] = {
    "Bäckereien": ["bakery"],
    "Autohäuser": ["car_dealer", "car_repair"],
    "Banken": ["bank"],
    "Versicherungen": ["insurance_agency"],
    "Gastronomie": ["restaurant", "cafe"],
    "Apotheken": ["pharmacy"],
    "Physio": ["physiotherapist"],
    "Fitness": ["gym"],
    "Handwerk": ["electrician", "plumber", "roofing_contractor", "painter", "general_contractor"],
    "Handel": ["clothing_store", "furniture_store", "hardware_store", "jewelry_store", "shoe_store", "book_store", "florist"],
    "Getränkehandel": ["liquor_store"],
    "Sportfachhandel": ["sporting_goods_store"],
    "Dienstleister": ["real_estate_agency", "accounting", "lawyer", "travel_agency"],
}

# Places kennt kein brand-Tag: bekannte Filialketten per Namen markieren.
KETTEN = re.compile(
    r"\b(aldi|lidl|rewe|edeka|penny|netto|kaufland|norma|dm|rossmann|tedi|nkd|kik|takko|deichmann|"
    r"ernsting|fielmann|apollo|mcdonald|burger king|subway|starbucks|kfc|vapiano|h&m|c&a|zara|"
    r"tchibo|thalia|hornbach|obi|bauhaus|toom|mediamarkt|saturn|expert|euronics|backwerk|"
    r"ditsch|kamps|mr\.? ?clean|mcfit|clever fit|fitx|jet|aral|shell|esso|total)\b",
    re.I,
)


class PlacesFehler(OsmFehler):
    pass


def _kopfzeilen() -> dict[str, str]:
    """Google-Login (ADC) mit Projekt für die Abrechnung.

    Places akzeptiert keine Vertex-Express-Keys (HTTP 401), daher immer ADC.
    """
    s = get_settings()
    import google.auth
    import google.auth.transport.requests

    cred, projekt = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    cred.refresh(google.auth.transport.requests.Request())
    kopf = {"Authorization": f"Bearer {cred.token}"}
    if s.google_cloud_project or projekt:
        kopf["X-Goog-User-Project"] = s.google_cloud_project or projekt
    return kopf


def _abfrage(branche: str, typen: list[str], lat: float, lon: float, radius_m: int, kopf: dict[str, str]) -> list[dict]:
    def holen() -> list[dict]:
        antwort = httpx.post(
            URL,
            headers={**kopf, "X-Goog-FieldMask": FELDER},
            json={
                "includedTypes": typen,
                "maxResultCount": 20,
                "languageCode": "de",
                "locationRestriction": {
                    "circle": {"center": {"latitude": lat, "longitude": lon}, "radius": float(min(radius_m, 50000))}
                },
            },
            timeout=20,
        )
        if antwort.status_code != 200:
            raise PlacesFehler(f"Places {branche}: HTTP {antwort.status_code} {antwort.text[:200]}")
        return antwort.json().get("places", [])

    return zwischengespeichert("places", holen, branche=branche, lat=round(lat, 4), lon=round(lon, 4), radius_m=radius_m)


def betriebe_im_umkreis(lat: float, lon: float, radius_km: float) -> list[Betrieb]:
    kopf = _kopfzeilen()
    radius_m = int(radius_km * 1000)

    def eine(paar: tuple[str, list[str]]) -> list[tuple[str, dict]] | str:
        branche, typen = paar
        try:
            return [(branche, p) for p in _abfrage(branche, typen, lat, lon, radius_m, kopf)]
        except (PlacesFehler, httpx.HTTPError) as e:
            return str(e)

    treffer: list[tuple[str, dict]] = []
    fehler: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for erg in pool.map(eine, BRANCHEN_TYPEN.items()):
            (fehler.append(erg) if isinstance(erg, str) else treffer.extend(erg))
    if not treffer:
        raise PlacesFehler("; ".join(fehler) or "Keine Betriebe gefunden")

    gesehen: dict[str, Betrieb] = {}
    for branche, p in treffer:
        if p["id"] in gesehen:
            continue
        name = (p.get("displayName") or {}).get("text", "").strip()
        ort = p.get("location") or {}
        if not name or "latitude" not in ort:
            continue
        gesehen[p["id"]] = Betrieb(
            osm_id=f"places/{p['id']}",
            name=name,
            branche=branche,
            osm_typ=f"google={p.get('primaryType') or (p.get('types') or ['?'])[0]}",
            adresse=p.get("formattedAddress"),
            lat=ort["latitude"],
            lon=ort["longitude"],
            website=p.get("websiteUri"),
            kette=bool(KETTEN.search(name)),
            entfernung_km=round(entfernung_km(lat, lon, ort["latitude"], ort["longitude"]), 2),
        )
    return sorted(gesehen.values(), key=lambda b: b.entfernung_km)
