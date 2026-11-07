"""Betriebe im Umkreis: erst Google Places (schnell), sonst OpenStreetMap (Ausweichweg)."""

import logging

from app.config import get_settings
from app.services import osm, places
from app.services.osm import Betrieb

logger = logging.getLogger(__name__)


def betriebe_im_umkreis(lat: float, lon: float, radius_km: float) -> tuple[list[Betrieb], str]:
    """Gibt (Betriebe, Quelle) zurück. Quelle: "Google Places" oder "OpenStreetMap"."""
    s = get_settings()
    if s.google_cloud_project:
        try:
            return places.betriebe_im_umkreis(lat, lon, radius_km), "Google Places"
        except Exception as e:  # API aus, Login fehlt, Quota – dann OSM
            logger.warning("Google Places nicht verfügbar, nutze OpenStreetMap: %s", e)
    return osm.betriebe_im_umkreis(lat, lon, radius_km), "OpenStreetMap"
