"""Kandidaten im Umkreis: suchen, vorfiltern, speichern, lesen."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.data import katalog
from app.db import get_session
from app.models import KANDIDAT_STATUS, InventarPosten, Kandidat, Sponsor, Unternehmen, Verein
from app.providers.cache import DemoDatenFehlen
from app.services import geo, osm, vorfilter

router = APIRouter(tags=["kandidaten"])


class KandidatAnsicht(BaseModel):
    id: int
    status: str
    entfernung_km: float
    vorfilter_score: int
    vorfilter_gruende: list[str]
    score: int | None
    sicherheit: str | None
    gruende: list[dict]
    paket_empfehlung: dict
    recherche_status: str
    unternehmen: Unternehmen


class SucheAntwort(BaseModel):
    kandidaten: list[KandidatAnsicht]
    luecken: list[dict]
    betriebe_gesamt: int
    ausgeschlossen_bestand: int
    hinweise: list[str]


def _ansicht(k: Kandidat, u: Unternehmen) -> KandidatAnsicht:
    return KandidatAnsicht(**k.model_dump(exclude={"verein_id", "unternehmen_id"}), unternehmen=u)


def freie_inventar_ids(session: Session, verein_id: int) -> tuple[list[str], bool]:
    """Freie Katalog-IDs. Ohne gepflegtes Inventar gilt der ganze Katalog als frei."""
    posten = session.exec(select(InventarPosten).where(InventarPosten.verein_id == verein_id)).all()
    if not posten:
        return list(katalog.nach_id()), False
    return [p.katalog_id for p in posten if p.verfuegbar and p.vergeben_an is None], True


@router.post("/vereine/{verein_id}/kandidaten", response_model=SucheAntwort)
def kandidaten_suchen(verein_id: int, anzahl: int = 30, session: Session = Depends(get_session)):
    verein = session.get(Verein, verein_id)
    if not verein:
        raise HTTPException(404, "Verein nicht gefunden")
    hinweise: list[str] = []

    try:
        if verein.lat is None or verein.lon is None:
            verein.lat, verein.lon = geo.geokodieren(verein.ort)
            session.add(verein)
            session.commit()
        betriebe = osm.betriebe_im_umkreis(verein.lat, verein.lon, verein.radius_km)
    except (geo.GeoFehler, osm.OsmFehler, DemoDatenFehlen) as e:
        raise HTTPException(502, str(e)) from e

    freie, gepflegt = freie_inventar_ids(session, verein_id)
    if not gepflegt:
        hinweise.append("Noch kein Angebots-Inventar gepflegt – alle Katalogpakete gelten als frei.")
    sponsoren = session.exec(select(Sponsor).where(Sponsor.verein_id == verein_id)).all()
    ergebnis = vorfilter.filtern(
        betriebe, freie, [s.firma for s in sponsoren], verein.radius_km, anzahl
    )

    # Unbearbeitete Kandidaten einer früheren Suche ersetzen, bearbeitete behalten.
    alte = session.exec(select(Kandidat).where(Kandidat.verein_id == verein_id)).all()
    behalten = set()
    for k in alte:
        if k.status == "neu" and k.recherche_status == "offen":
            session.delete(k)
        else:
            behalten.add(k.unternehmen_id)
    session.commit()

    for v in ergebnis.kandidaten:
        b = v.betrieb
        u = session.exec(select(Unternehmen).where(Unternehmen.osm_id == b.osm_id)).first()
        if not u:
            u = Unternehmen(**b.model_dump(exclude={"entfernung_km", "kette"}))
            session.add(u)
            session.commit()
            session.refresh(u)
        if u.id in behalten:
            continue
        session.add(
            Kandidat(
                verein_id=verein_id,
                unternehmen_id=u.id,
                entfernung_km=b.entfernung_km,
                vorfilter_score=v.score,
                vorfilter_gruende=v.gruende,
                paket_empfehlung={"passende_pakete": v.passende_pakete},
            )
        )
    session.commit()

    return SucheAntwort(
        kandidaten=kandidaten_lesen(verein_id, session),
        luecken=ergebnis.luecken,
        betriebe_gesamt=ergebnis.betriebe_gesamt,
        ausgeschlossen_bestand=ergebnis.ausgeschlossen_bestand,
        hinweise=hinweise,
    )


@router.get("/vereine/{verein_id}/kandidaten", response_model=list[KandidatAnsicht])
def kandidaten_lesen(verein_id: int, session: Session = Depends(get_session)):
    zeilen = session.exec(
        select(Kandidat, Unternehmen)
        .join(Unternehmen, Kandidat.unternehmen_id == Unternehmen.id)
        .where(Kandidat.verein_id == verein_id)
    ).all()
    ansichten = [_ansicht(k, u) for k, u in zeilen]
    return sorted(ansichten, key=lambda a: (-(a.score or a.vorfilter_score), a.entfernung_km))


class StatusAenderung(BaseModel):
    status: str


@router.patch("/kandidaten/{kandidat_id}/status", response_model=KandidatAnsicht)
def status_setzen(kandidat_id: int, daten: StatusAenderung, session: Session = Depends(get_session)):
    if daten.status not in KANDIDAT_STATUS:
        raise HTTPException(422, f"Status muss einer von {', '.join(KANDIDAT_STATUS)} sein")
    k = session.get(Kandidat, kandidat_id)
    if not k:
        raise HTTPException(404, "Kandidat nicht gefunden")
    k.status = daten.status
    session.add(k)
    session.commit()
    session.refresh(k)
    return _ansicht(k, session.get(Unternehmen, k.unternehmen_id))
