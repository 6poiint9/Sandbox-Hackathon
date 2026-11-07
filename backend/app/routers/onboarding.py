from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.providers.cache import DemoDatenFehlen
from app.providers.websuche import WebsucheFehler, websuche
from app.services.auth import BEGRENZER, Inhaber, client_ip, inhaber
from app.services.onboarding import ProfilVorschlag, analysieren

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class AnalyseAnfrage(BaseModel):
    website: str
    ort: str = ""


@router.post("/analyse", response_model=ProfilVorschlag)
def analyse(anfrage: AnalyseAnfrage, request: Request, wer: Inhaber = Depends(inhaber)) -> ProfilVorschlag:
    # Kostenbremse: Website-Analysen nutzen bezahlte APIs (Exa, Gemini). Gäste zusätzlich je IP,
    # weil ein neues Gast-Cookie nichts kostet.
    if wer.konto:
        BEGRENZER.pruefen(f"analyse:{wer.konto.id}", 20, 3600)
    else:
        BEGRENZER.pruefen(f"analyse-ip:{client_ip(request)}", 10, 3600)
    try:
        return analysieren(websuche(), anfrage.website.strip()[:300], anfrage.ort.strip()[:100])
    except (WebsucheFehler, DemoDatenFehlen) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
