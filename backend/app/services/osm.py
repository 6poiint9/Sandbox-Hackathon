"""Betriebe im Umkreis aus OpenStreetMap (Overpass API).

Holt benannte Betriebe (shop, craft, office, Gastronomie, Banken, healthcare,
Fitness), übersetzt OSM-Tags in unsere Branchen (passend zu den
`zielbranchen` im Katalog) und führt Duplikate zusammen.
"""

import httpx
from pydantic import BaseModel

from app.providers.cache import zwischengespeichert
from app.services.geo import USER_AGENT, entfernung_km

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

GASTRO = "restaurant|cafe|pub|bar|biergarten|fast_food|ice_cream"
AMENITY = f"{GASTRO}|bank|pharmacy|fuel|car_rental|driving_school|nursing_home|dentist|doctors|clinic"


class OsmFehler(RuntimeError):
    pass


class Betrieb(BaseModel):
    osm_id: str
    name: str
    branche: str
    osm_typ: str
    adresse: str | None = None
    lat: float
    lon: float
    website: str | None = None
    kette: bool = False  # OSM-Tag brand/brand:wikidata vorhanden
    entfernung_km: float


# (Tag, Wert oder "*") -> Branche. Spezielleres zuerst.
BRANCHEN: list[tuple[str, str, str]] = [
    ("shop", "bakery", "Bäckereien"),
    ("shop", "pastry", "Bäckereien"),
    ("shop", "butcher", "Familienbetriebe"),
    ("shop", "car", "Autohäuser"),
    ("shop", "car_repair", "Autohäuser"),
    ("shop", "motorcycle", "Autohäuser"),
    ("shop", "optician", "Optiker"),
    ("shop", "sports", "Sportfachhandel"),
    ("shop", "beverages", "Getränkehandel"),
    ("shop", "copyshop", "Druckerei"),
    ("craft", "brewery", "Brauerei"),
    ("craft", "printer", "Druckerei"),
    ("craft", "*", "Handwerk"),
    ("amenity", "bank", "Banken"),
    ("amenity", "pharmacy", "Apotheken"),
    ("amenity", "driving_school", "Dienstleister"),
    ("amenity", "nursing_home", "Pflege"),
    ("amenity", "fuel", "Autohäuser"),
    ("amenity", "car_rental", "Autohäuser"),
    ("amenity", "dentist", "Dienstleister"),
    ("amenity", "doctors", "Dienstleister"),
    ("amenity", "clinic", "Pflege"),
    ("healthcare", "physiotherapist", "Physio"),
    ("healthcare", "*", "Pflege"),
    ("leisure", "fitness_centre", "Fitness"),
    ("office", "insurance", "Versicherungen"),
    ("office", "energy_supplier", "Stadtwerke"),
    ("office", "logistics", "Logistik"),
    ("office", "*", "Dienstleister"),
    ("shop", "*", "Handel"),
]


def branche_von(tags: dict) -> tuple[str, str] | None:
    for schluessel, wert, branche in BRANCHEN:
        if schluessel not in tags:
            continue
        if schluessel == "amenity" and tags["amenity"] in GASTRO.split("|"):
            return "Gastronomie", f"amenity={tags['amenity']}"
        if wert == "*" or tags[schluessel] == wert:
            return branche, f"{schluessel}={tags[schluessel]}"
    if tags.get("amenity") in GASTRO.split("|"):
        return "Gastronomie", f"amenity={tags['amenity']}"
    return None


def _adresse(tags: dict) -> str | None:
    strasse = " ".join(filter(None, [tags.get("addr:street"), tags.get("addr:housenumber")]))
    ort = " ".join(filter(None, [tags.get("addr:postcode"), tags.get("addr:city")]))
    text = ", ".join(filter(None, [strasse, ort]))
    return text or None


def _website(tags: dict) -> str | None:
    for k in ("website", "contact:website", "url"):
        if tags.get(k):
            w = tags[k].strip()
            return w if "://" in w else f"https://{w}"
    return None


# Eine Abfrage je Kategorie: Eine Sammelabfrage über 10+ km läuft bei Overpass ins Zeitlimit.
KATEGORIEN = {
    "shop": 'nwr["shop"]["name"]',
    "craft": 'nwr["craft"]["name"]',
    "office": 'nwr["office"]["name"]',
    "amenity": f'nwr["amenity"~"^({AMENITY})$"]["name"]',
    "healthcare": 'nwr["healthcare"]["name"]',
    "fitness": 'nwr["leisure"="fitness_centre"]["name"]',
}


def overpass_abfrage(filter_: str, lat: float, lon: float, radius_m: int) -> str:
    return f"[out:json][timeout:60];{filter_}(around:{radius_m},{lat},{lon});out center tags;"


def _kategorie_holen(name: str, filter_: str, lat: float, lon: float, radius_m: int) -> list[dict]:
    def holen() -> list[dict]:
        antwort = httpx.post(
            OVERPASS_URL,
            data={"data": overpass_abfrage(filter_, lat, lon, radius_m)},
            headers={"User-Agent": USER_AGENT},
            timeout=90,
        )
        antwort.raise_for_status()
        daten = antwort.json()
        # Bei Zeitüberschreitung liefert Overpass HTTP 200, leere Liste und eine "remark".
        if daten.get("remark") and not daten.get("elements"):
            raise OsmFehler(f"Overpass ({name}): {daten['remark']}")
        return daten.get("elements", [])

    try:
        return zwischengespeichert(
            "overpass", holen, kategorie=name, lat=round(lat, 4), lon=round(lon, 4), radius_m=radius_m
        )
    except httpx.HTTPError as e:
        raise OsmFehler(f"Overpass nicht erreichbar ({name}): {e}") from e


def _roh_holen(lat: float, lon: float, radius_m: int) -> list[dict]:
    elemente: list[dict] = []
    fehler: list[str] = []
    for name, filter_ in KATEGORIEN.items():
        try:
            elemente.extend(_kategorie_holen(name, filter_, lat, lon, radius_m))
        except OsmFehler as e:
            fehler.append(str(e))  # eine Kategorie darf ausfallen
    if fehler and not elemente:
        raise OsmFehler("; ".join(fehler))
    return elemente


def _schluessel(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def betriebe_im_umkreis(lat: float, lon: float, radius_km: float) -> list[Betrieb]:
    elemente = _roh_holen(lat, lon, int(radius_km * 1000))
    gesehen: dict[str, Betrieb] = {}
    for el in elemente:
        tags = el.get("tags") or {}
        name = (tags.get("name") or "").strip()
        zuordnung = branche_von(tags)
        punkt = el if "lat" in el else el.get("center") or {}
        if not name or not zuordnung or "lat" not in punkt:
            continue
        branche, osm_typ = zuordnung
        betrieb = Betrieb(
            osm_id=f"{el['type']}/{el['id']}",
            name=name,
            branche=branche,
            osm_typ=osm_typ,
            adresse=_adresse(tags),
            lat=punkt["lat"],
            lon=punkt["lon"],
            website=_website(tags),
            kette=bool(tags.get("brand:wikidata") or tags.get("brand")),
            entfernung_km=round(entfernung_km(lat, lon, punkt["lat"], punkt["lon"]), 2),
        )
        # Duplikat = gleicher Name, weniger als 300 m entfernt (z. B. Node + Gebäude)
        key = _schluessel(name)
        alt = gesehen.get(key)
        if alt and entfernung_km(alt.lat, alt.lon, betrieb.lat, betrieb.lon) < 0.3:
            if not alt.website and betrieb.website:
                alt.website = betrieb.website
            if not alt.adresse and betrieb.adresse:
                alt.adresse = betrieb.adresse
            continue
        gesehen[key if not alt else f"{key}-{betrieb.osm_id}"] = betrieb
    return sorted(gesehen.values(), key=lambda b: b.entfernung_km)
