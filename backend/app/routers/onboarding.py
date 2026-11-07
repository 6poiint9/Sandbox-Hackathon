from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.providers.cache import DemoDatenFehlen
from app.providers.websuche import WebsucheFehler, websuche
from app.services.onboarding import ProfilVorschlag, analysieren

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class AnalyseAnfrage(BaseModel):
    website: str
    ort: str


@router.post("/analyse", response_model=ProfilVorschlag)
def analyse(anfrage: AnalyseAnfrage) -> ProfilVorschlag:
    try:
        return analysieren(websuche(), anfrage.website.strip(), anfrage.ort.strip())
    except (WebsucheFehler, DemoDatenFehlen) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
