from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models import Konto
from app.providers.cache import DemoDatenFehlen
from app.providers.websuche import WebsucheFehler, websuche
from app.services.auth import BEGRENZER, aktuelles_konto
from app.services.onboarding import ProfilVorschlag, analysieren

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class AnalyseAnfrage(BaseModel):
    website: str
    ort: str = ""


@router.post("/analyse", response_model=ProfilVorschlag)
def analyse(anfrage: AnalyseAnfrage, konto: Konto = Depends(aktuelles_konto)) -> ProfilVorschlag:
    # Kostenbremse: Website-Analysen nutzen bezahlte APIs (Exa, Gemini)
    BEGRENZER.pruefen(f"analyse:{konto.id}", 20, 3600)
    try:
        return analysieren(websuche(), anfrage.website.strip()[:300], anfrage.ort.strip()[:100])
    except (WebsucheFehler, DemoDatenFehlen) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
