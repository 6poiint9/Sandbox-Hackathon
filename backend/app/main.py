"""FastAPI-App für Sponsorenkompass."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.data import katalog
from app import models  # noqa: F401 - registriert die Tabellen
from app.db import init_db
from app.routers import analyse, crm, kandidaten, konto, landing, onboarding, vereine
from app.services.auth import CSRF_HEADER, zugriff


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(title="Sponsorenkompass", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", CSRF_HEADER],
)

SICHER = {"GET", "HEAD", "OPTIONS"}
SICHERHEITS_HEADER = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
# Swagger UI (/docs) lädt Skript und Stil vom CDN und startet per Inline-Skript;
# nur dafür eine gelockerte Richtlinie, alles andere bleibt bei default-src 'none'.
DOCS_CSP = (
    "default-src 'none'; frame-ancestors 'none'; "
    "script-src https://cdn.jsdelivr.net 'unsafe-inline'; style-src https://cdn.jsdelivr.net; "
    "img-src https://fastapi.tiangolo.com data:; connect-src 'self'"
)


@app.middleware("http")
async def csrf_und_header(request: Request, call_next):
    """CSRF: zustandsändernde Anfragen brauchen unseren Header (Browser senden ihn
    cross-site nur nach CORS-Freigabe) und, falls vorhanden, einen erlaubten Origin."""
    if request.method not in SICHER:
        origin = request.headers.get("origin")
        erlaubt = {settings.frontend_url.rstrip("/"), str(request.base_url).rstrip("/")}
        if request.headers.get(CSRF_HEADER) != "1" or (origin and origin.rstrip("/") not in erlaubt):
            return JSONResponse({"detail": "Anfrage abgelehnt (CSRF-Schutz)."}, status_code=403)
    antwort = await call_next(request)
    if request.url.path == app.docs_url:
        antwort.headers["Content-Security-Policy"] = DOCS_CSP
    for k, v in SICHERHEITS_HEADER.items():
        antwort.headers.setdefault(k, v)
    if settings.cookie_secure:
        antwort.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return antwort
app.include_router(onboarding.router, dependencies=[Depends(zugriff)])
app.include_router(vereine.router, dependencies=[Depends(zugriff)])
app.include_router(kandidaten.router, dependencies=[Depends(zugriff)])
app.include_router(analyse.router, dependencies=[Depends(zugriff)])
app.include_router(crm.router, dependencies=[Depends(zugriff)])
app.include_router(landing.router)
app.include_router(konto.router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "exa_konfiguriert": bool(settings.exa_api_key),
        "katalog_eintraege": len(katalog.laden()),
    }


@app.get("/katalog")
def katalog_lesen() -> list[dict]:
    return katalog.laden()
