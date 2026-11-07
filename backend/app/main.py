"""FastAPI-App für Sponsorenkompass."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.data import katalog
from app import models  # noqa: F401 - registriert die Tabellen
from app.db import init_db
from app.routers import analyse, crm, kandidaten, onboarding, vereine


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(title="Sponsorenkompass", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(onboarding.router)
app.include_router(vereine.router)
app.include_router(kandidaten.router)
app.include_router(analyse.router)
app.include_router(crm.router)


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
