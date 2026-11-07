"""Kandidaten im Umkreis: suchen, vorfiltern, speichern, lesen."""

from collections import Counter
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.data import katalog
from app.db import get_session
from app.models import KANDIDAT_STATUS, Aktivitaet, InventarPosten, Kandidat, Sponsor, Unternehmen, Verein
from app.providers.cache import DemoDatenFehlen
from app.services import freigabe, geo, osm, recherche, umkreis, vorfilter
from app.services.auth import Inhaber, zugriff

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
    zusammenfassung: str | None = None
    quellen: list[dict] = []
    recherche_status: str
    recherche_fehler: str | None = None
    ansprechpartner: str | None = None
    email: str | None = None
    telefon: str | None = None
    naechster_schritt: str | None = None
    wiedervorlage: date | None = None
    notiz: str | None = None
    sponsor_id: int | None = None
    gesperrt: bool = False  # ohne Abo: nur Branche und Entfernung, Rest geschwärzt
    unternehmen: Unternehmen


class SucheAntwort(BaseModel):
    kandidaten: list[KandidatAnsicht]
    luecken: list[dict]
    betriebe_gesamt: int
    ausgeschlossen_bestand: int
    hinweise: list[str]


def _ansicht(k: Kandidat, u: Unternehmen) -> KandidatAnsicht:
    return KandidatAnsicht(**k.model_dump(exclude={"verein_id", "unternehmen_id"}), unternehmen=u)


def _gesperrt(k: Kandidat, u: Unternehmen) -> KandidatAnsicht:
    """Nur was neugierig macht, nichts was den Betrieb verrät. Ort auf ~1 km gerundet."""
    platzhalter = Unternehmen(id=None, osm_id="", name=freigabe.GESPERRT_NAME, branche=u.branche,
                              lat=round(u.lat, 2), lon=round(u.lon, 2))
    return KandidatAnsicht(
        id=k.id, status="neu", entfernung_km=round(k.entfernung_km, 1), vorfilter_score=k.vorfilter_score,
        vorfilter_gruende=[], score=None, sicherheit=None, gruende=[], paket_empfehlung={},
        recherche_status="gesperrt", gesperrt=True, unternehmen=platzhalter,
    )


def freie_inventar_ids(session: Session, verein_id: int) -> tuple[list[str], bool]:
    """Freie Katalog-IDs. Ohne gepflegtes Inventar gilt der ganze Katalog als frei."""
    posten = session.exec(select(InventarPosten).where(InventarPosten.verein_id == verein_id)).all()
    if not posten:
        return list(katalog.nach_id()), False
    return [p.katalog_id for p in posten if p.verfuegbar and p.vergeben_an is None], True


@router.post("/vereine/{verein_id}/kandidaten", response_model=SucheAntwort)
def kandidaten_suchen(
    verein_id: int, anzahl: int = 30, session: Session = Depends(get_session), wer: Inhaber | None = Depends(zugriff)
):
    verein = session.get(Verein, verein_id)
    if not verein:
        raise HTTPException(404, "Verein nicht gefunden")
    hinweise: list[str] = []

    try:
        if verein.lat is None or verein.lon is None:
            try:
                verein.lat, verein.lon = geo.geokodieren(verein.sportstaette or verein.ort)
            except geo.GeoFehler:
                verein.lat, verein.lon = geo.geokodieren(verein.ort)
            session.add(verein)
            session.commit()
        betriebe, quelle = umkreis.betriebe_im_umkreis(verein.lat, verein.lon, verein.radius_km)
        hinweise.append(f"Betriebe aus {quelle}")
    except (geo.GeoFehler, osm.OsmFehler, DemoDatenFehlen) as e:
        raise HTTPException(502, str(e)) from e

    freie, gepflegt = freie_inventar_ids(session, verein_id)
    if not gepflegt:
        hinweise.append("Noch kein Angebots-Inventar gepflegt – alle Katalogpakete gelten als frei.")
    sponsoren = session.exec(select(Sponsor).where(Sponsor.verein_id == verein_id)).all()
    ergebnis = vorfilter.filtern(
        betriebe, freie, [s.firma for s in sponsoren], verein.radius_km, anzahl
    )
    verein.luecken = ergebnis.luecken
    verein.betriebe_im_umkreis = ergebnis.betriebe_gesamt
    session.add(verein)
    session.commit()

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
        kandidaten=kandidaten_lesen(verein_id, session, wer),
        luecken=ergebnis.luecken,
        betriebe_gesamt=ergebnis.betriebe_gesamt,
        ausgeschlossen_bestand=ergebnis.ausgeschlossen_bestand,
        hinweise=hinweise,
    )


@router.get("/vereine/{verein_id}/kandidaten", response_model=list[KandidatAnsicht])
def kandidaten_lesen(verein_id: int, session: Session = Depends(get_session), wer: Inhaber | None = Depends(zugriff)):
    zeilen = session.exec(
        select(Kandidat, Unternehmen)
        .join(Unternehmen, Kandidat.unternehmen_id == Unternehmen.id)
        .where(Kandidat.verein_id == verein_id)
    ).all()
    # Interne Aufrufe (ohne Anfrage) bekommen keine Freischaltung: im Zweifel sperren.
    abo = isinstance(wer, Inhaber) and wer.abo
    frei = freigabe.freie_ids(session, verein_id)
    ansichten = [_ansicht(k, u) if abo or k.id in frei else _gesperrt(k, u) for k, u in zeilen]
    # Freie vor gesperrten; darin geprüfte zuerst (nach Score), danach ungeprüfte nach Vorfilter
    return sorted(
        ansichten,
        key=lambda a: (a.gesperrt, a.recherche_status != "fertig", -((a.score if a.recherche_status == "fertig" else a.vorfilter_score) or 0), a.entfernung_km),
    )


class StatusAenderung(BaseModel):
    status: str


@router.patch("/kandidaten/{kandidat_id}/status", response_model=KandidatAnsicht)
def status_setzen(kandidat_id: int, daten: StatusAenderung, session: Session = Depends(get_session)):
    if daten.status not in KANDIDAT_STATUS:
        raise HTTPException(422, f"Status muss einer von {', '.join(KANDIDAT_STATUS)} sein")
    k = session.get(Kandidat, kandidat_id)
    if not k:
        raise HTTPException(404, "Kandidat nicht gefunden")
    if k.status != daten.status:
        session.add(Aktivitaet(verein_id=k.verein_id, kandidat_id=k.id, art="status",
                               text=f"Status: {k.status} → {daten.status}"))
    k.status = daten.status
    session.add(k)
    session.commit()
    session.refresh(k)
    return _ansicht(k, session.get(Unternehmen, k.unternehmen_id))


# --- Recherche und Bewertung ------------------------------------------------


class RechercheStart(BaseModel):
    gestartet: int
    kandidat_ids: list[int]


class RechercheStatus(BaseModel):
    gesamt: int
    status: dict[str, int]
    fertig: bool


@router.post("/vereine/{verein_id}/recherche", response_model=RechercheStart)
def recherche_starten(
    verein_id: int,
    hintergrund: BackgroundTasks,
    anzahl: int = 15,
    kandidat_id: int | None = None,
    session: Session = Depends(get_session),
    wer: Inhaber = Depends(zugriff),
):
    """Recherchiert die besten `anzahl` offenen Kandidaten – oder genau `kandidat_id`.

    Ohne Abo nur die freien Kandidaten (Kostenbremse, Sperre bleibt serverseitig).
    """
    if not session.get(Verein, verein_id):
        raise HTTPException(404, "Verein nicht gefunden")
    offen = [
        k
        for k in session.exec(select(Kandidat).where(Kandidat.verein_id == verein_id)).all()
        if k.recherche_status in ("offen", "fehler")
    ]
    if kandidat_id is not None:
        offen = [k for k in offen if k.id == kandidat_id]
    if not wer.abo:
        frei = freigabe.freie_ids(session, verein_id)
        offen = [k for k in offen if k.id in frei]
    offen.sort(key=lambda k: (-k.vorfilter_score, k.entfernung_km))
    auswahl = offen[:anzahl]
    for k in auswahl:
        k.recherche_status = "wartet"
        k.recherche_fehler = None
        session.add(k)
    session.commit()
    ids = [k.id for k in auswahl]
    freie, _ = freie_inventar_ids(session, verein_id)
    if ids:
        hintergrund.add_task(recherche.alle_recherchieren, ids, freie)
    return RechercheStart(gestartet=len(ids), kandidat_ids=ids)


@router.get("/vereine/{verein_id}/recherche/status", response_model=RechercheStatus)
def recherche_status(verein_id: int, session: Session = Depends(get_session)):
    kandidaten = session.exec(select(Kandidat).where(Kandidat.verein_id == verein_id)).all()
    zaehler = Counter(k.recherche_status for k in kandidaten)
    return RechercheStatus(
        gesamt=len(kandidaten),
        status=dict(zaehler),
        fertig=zaehler["wartet"] == 0 and zaehler["laeuft"] == 0,
    )


# --- Kompletter Hintergrundauftrag (Onboarding) -----------------------------


class AnalyseStart(BaseModel):
    email: str | None = None


class AnalyseZustand(BaseModel):
    suche_status: str
    suche_fehler: str | None
    benachrichtigung_email: str | None
    email_verfuegbar: bool
    recherche: RechercheStatus


@router.post("/vereine/{verein_id}/analyse", response_model=AnalyseZustand)
def analyse_starten(
    verein_id: int,
    hintergrund: BackgroundTasks,
    daten: AnalyseStart | None = None,
    recherche_anzahl: int = 10,
    session: Session = Depends(get_session),
    wer: Inhaber = Depends(zugriff),
):
    """Startet Umkreissuche + Recherche im Hintergrund und kehrt sofort zurück."""
    from app.services import analyse_job

    verein = session.get(Verein, verein_id)
    if not verein:
        raise HTTPException(404, "Verein nicht gefunden")
    if verein.suche_status != "laeuft":
        verein.suche_status = "laeuft"
        verein.suche_fehler = None
        if daten and daten.email:
            verein.benachrichtigung_email = daten.email.strip()
        session.add(verein)
        session.commit()
        # Ohne Abo nur die freien 3: Der Job recherchiert in Vorfilter-Reihenfolge, also genau diese.
        anzahl = recherche_anzahl if wer.abo else min(recherche_anzahl, freigabe.FREI_ANZAHL)
        hintergrund.add_task(analyse_job.ausfuehren, verein_id, anzahl)
    return analyse_zustand(verein_id, session)


@router.get("/vereine/{verein_id}/analyse", response_model=AnalyseZustand)
def analyse_zustand(verein_id: int, session: Session = Depends(get_session)):
    from app.services import mail

    verein = session.get(Verein, verein_id)
    if not verein:
        raise HTTPException(404, "Verein nicht gefunden")
    return AnalyseZustand(
        suche_status=verein.suche_status or "offen",
        suche_fehler=verein.suche_fehler,
        benachrichtigung_email=verein.benachrichtigung_email,
        email_verfuegbar=mail.verfuegbar(),
        recherche=recherche_status(verein_id, session),
    )


class EmailEintrag(BaseModel):
    email: str


@router.put("/vereine/{verein_id}/benachrichtigung", response_model=AnalyseZustand)
def benachrichtigung_setzen(verein_id: int, daten: EmailEintrag, session: Session = Depends(get_session)):
    """E-Mail für die Fertig-Meldung. Ist die Analyse schon fertig, geht die Mail sofort raus."""
    from app.services import analyse_job

    verein = session.get(Verein, verein_id)
    if not verein:
        raise HTTPException(404, "Verein nicht gefunden")
    if "@" not in daten.email or "." not in daten.email.split("@")[-1]:
        raise HTTPException(422, "Bitte eine gültige E-Mail-Adresse eintragen")
    verein.benachrichtigung_email = daten.email.strip()
    session.add(verein)
    session.commit()
    if verein.suche_status == "fertig":
        analyse_job.benachrichtigen(verein_id)
    return analyse_zustand(verein_id, session)
