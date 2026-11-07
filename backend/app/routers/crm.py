"""CRM: Sponsoren und Kandidaten pflegen, Verlauf, Aufgaben, Assets mit Vergaben."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.data import katalog
from app.db import get_session
from app.models import (
    AKTIVITAET_ARTEN,
    KANDIDAT_STATUS,
    Aktivitaet,
    AssetVergabe,
    InventarPosten,
    Kandidat,
    Sponsor,
    Unternehmen,
    Verein,
)
from app.services.auth import verein_von
from app.services.potenzial import belegte_einheiten, preis_band

router = APIRouter(tags=["crm"])

SPONSOR_STATUS = ("aktiv", "verlaengerung", "beendet")


def _hole(session: Session, modell, id_: int, name: str):
    obj = session.get(modell, id_)
    if not obj:
        raise HTTPException(404, f"{name} nicht gefunden")
    return obj


def _protokoll(session: Session, verein_id: int, text: str, art: str = "status", *, sponsor_id=None, kandidat_id=None):
    session.add(Aktivitaet(verein_id=verein_id, sponsor_id=sponsor_id, kandidat_id=kandidat_id, art=art, text=text))


def _uebernehmen(obj, daten: BaseModel) -> list[str]:
    geaendert = []
    for feld, wert in daten.model_dump(exclude_unset=True).items():
        if getattr(obj, feld) != wert:
            setattr(obj, feld, wert)
            geaendert.append(feld)
    return geaendert


# --- Sponsoren --------------------------------------------------------------


class SponsorAenderung(BaseModel):
    firma: str | None = None
    website: str | None = None
    gegenleistung: str | None = None
    gegenleistung_text: str | None = None
    betrag_eur: int | None = None
    laufzeit_bis: date | None = None
    ansprechpartner: str | None = None
    email: str | None = None
    telefon: str | None = None
    status: str | None = None
    naechster_schritt: str | None = None
    wiedervorlage: date | None = None
    notiz: str | None = None


@router.patch("/sponsoren/{sponsor_id}", response_model=Sponsor)
def sponsor_aendern(sponsor_id: int, daten: SponsorAenderung, session: Session = Depends(get_session)) -> Sponsor:
    s = _hole(session, Sponsor, sponsor_id, "Sponsor")
    if daten.status and daten.status not in SPONSOR_STATUS:
        raise HTTPException(422, f"Status muss einer von {', '.join(SPONSOR_STATUS)} sein")
    alter_status = s.status
    _uebernehmen(s, daten)
    if daten.status and daten.status != alter_status:
        _protokoll(session, s.verein_id, f"Status: {alter_status} → {daten.status}", sponsor_id=s.id)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


# --- Kandidaten (CRM-Felder) ------------------------------------------------


class KandidatAenderung(BaseModel):
    status: str | None = None
    ansprechpartner: str | None = None
    email: str | None = None
    telefon: str | None = None
    naechster_schritt: str | None = None
    wiedervorlage: date | None = None
    notiz: str | None = None


@router.patch("/kandidaten/{kandidat_id}", response_model=Kandidat)
def kandidat_aendern(kandidat_id: int, daten: KandidatAenderung, session: Session = Depends(get_session)) -> Kandidat:
    k = _hole(session, Kandidat, kandidat_id, "Kandidat")
    if daten.status and daten.status not in KANDIDAT_STATUS:
        raise HTTPException(422, f"Status muss einer von {', '.join(KANDIDAT_STATUS)} sein")
    alter_status = k.status
    _uebernehmen(k, daten)
    if daten.status and daten.status != alter_status:
        _protokoll(session, k.verein_id, f"Status: {alter_status} → {daten.status}", kandidat_id=k.id)
    session.add(k)
    session.commit()
    session.refresh(k)
    return k


class Uebernahme(BaseModel):
    betrag_eur: int | None = None
    laufzeit_bis: date | None = None
    asset_id: int | None = None
    anzahl: int = 1


@router.post("/kandidaten/{kandidat_id}/zum-sponsor", response_model=Sponsor)
def zum_sponsor(kandidat_id: int, daten: Uebernahme, session: Session = Depends(get_session)) -> Sponsor:
    """Zusage: Kandidat wird Bestandssponsor, optional mit Asset-Vergabe."""
    k = _hole(session, Kandidat, kandidat_id, "Kandidat")
    if k.sponsor_id:
        return _hole(session, Sponsor, k.sponsor_id, "Sponsor")
    u = _hole(session, Unternehmen, k.unternehmen_id, "Unternehmen")
    pe = k.paket_empfehlung or {}
    paket_ids = pe.get("katalog_ids") or []
    s = Sponsor(
        verein_id=k.verein_id, firma=u.name, website=u.website,
        gegenleistung=paket_ids[0] if paket_ids else None,
        gegenleistung_text=" + ".join(pe.get("namen") or []) or None,
        betrag_eur=daten.betrag_eur, laufzeit_bis=daten.laufzeit_bis,
        ansprechpartner=k.ansprechpartner, email=k.email, telefon=k.telefon,
    )
    session.add(s)
    session.commit()
    session.refresh(s)
    if daten.asset_id:
        asset = _hole(session, InventarPosten, daten.asset_id, "Asset")
        if asset.verein_id != k.verein_id:
            raise HTTPException(404, "Asset nicht gefunden")
        session.add(AssetVergabe(asset_id=asset.id, sponsor_id=s.id, anzahl=daten.anzahl,
                                 preis_eur=daten.betrag_eur, bis=daten.laufzeit_bis))
    k.status = "zusage"
    k.sponsor_id = s.id
    session.add(k)
    _protokoll(session, k.verein_id, f"Zusage – als Sponsor übernommen ({s.firma})", "vertrag", kandidat_id=k.id, sponsor_id=s.id)
    session.commit()
    session.refresh(s)
    return s


# --- Aktivitäten ------------------------------------------------------------


class AktivitaetNeu(BaseModel):
    art: str = "notiz"
    text: str
    sponsor_id: int | None = None
    kandidat_id: int | None = None
    zeitpunkt: datetime | None = None


@router.get("/vereine/{verein_id}/aktivitaeten", response_model=list[Aktivitaet])
def aktivitaeten(verein_id: int, sponsor_id: int | None = None, kandidat_id: int | None = None,
                 session: Session = Depends(get_session)):
    abfrage = select(Aktivitaet).where(Aktivitaet.verein_id == verein_id)
    if sponsor_id is not None:
        abfrage = abfrage.where(Aktivitaet.sponsor_id == sponsor_id)
    if kandidat_id is not None:
        abfrage = abfrage.where(Aktivitaet.kandidat_id == kandidat_id)
    return sorted(session.exec(abfrage).all(), key=lambda a: a.zeitpunkt, reverse=True)


@router.post("/vereine/{verein_id}/aktivitaeten", response_model=Aktivitaet)
def aktivitaet_anlegen(verein_id: int, daten: AktivitaetNeu, session: Session = Depends(get_session)) -> Aktivitaet:
    _hole(session, Verein, verein_id, "Verein")
    if daten.art not in AKTIVITAET_ARTEN:
        raise HTTPException(422, f"Art muss eine von {', '.join(AKTIVITAET_ARTEN)} sein")
    if not daten.text.strip():
        raise HTTPException(422, "Text fehlt")
    # Referenzierte Objekte müssen zum selben Verein gehören
    for art, id_ in (("sponsor_id", daten.sponsor_id), ("kandidat_id", daten.kandidat_id)):
        if id_ is not None and verein_von(session, art, id_) != verein_id:
            raise HTTPException(404, "Nicht gefunden")
    a = Aktivitaet(verein_id=verein_id, **daten.model_dump(exclude_none=True))
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


@router.delete("/aktivitaeten/{aktivitaet_id}", status_code=204)
def aktivitaet_loeschen(aktivitaet_id: int, session: Session = Depends(get_session)) -> None:
    session.delete(_hole(session, Aktivitaet, aktivitaet_id, "Aktivität"))
    session.commit()


# --- Aufgaben ---------------------------------------------------------------


class Aufgabe(BaseModel):
    art: str  # wiedervorlage, vertragsende
    faellig: date
    titel: str
    text: str
    sponsor_id: int | None = None
    kandidat_id: int | None = None
    ueberfaellig: bool


@router.get("/vereine/{verein_id}/aufgaben", response_model=list[Aufgabe])
def aufgaben(verein_id: int, tage: int = 14, session: Session = Depends(get_session)):
    heute = date.today()
    grenze = heute + timedelta(days=tage)
    liste: list[Aufgabe] = []
    for s in session.exec(select(Sponsor).where(Sponsor.verein_id == verein_id)).all():
        if s.wiedervorlage and s.wiedervorlage <= grenze:
            liste.append(Aufgabe(art="wiedervorlage", faellig=s.wiedervorlage, titel=s.firma,
                                 text=s.naechster_schritt or "Wiedervorlage", sponsor_id=s.id,
                                 ueberfaellig=s.wiedervorlage < heute))
        if s.laufzeit_bis and s.status != "beendet" and s.laufzeit_bis <= heute + timedelta(days=90):
            liste.append(Aufgabe(art="vertragsende", faellig=s.laufzeit_bis, titel=s.firma,
                                 text="Sponsoring läuft aus – Verlängerung ansprechen", sponsor_id=s.id,
                                 ueberfaellig=s.laufzeit_bis < heute))
    zeilen = session.exec(
        select(Kandidat, Unternehmen).join(Unternehmen, Kandidat.unternehmen_id == Unternehmen.id)
        .where(Kandidat.verein_id == verein_id)
    ).all()
    for k, u in zeilen:
        if k.wiedervorlage and k.wiedervorlage <= grenze and k.status not in ("zusage", "absage"):
            liste.append(Aufgabe(art="wiedervorlage", faellig=k.wiedervorlage, titel=u.name,
                                 text=k.naechster_schritt or "Nachfassen", kandidat_id=k.id,
                                 ueberfaellig=k.wiedervorlage < heute))
    return sorted(liste, key=lambda a: a.faellig)


# --- Assets -----------------------------------------------------------------


class VergabeAnsicht(BaseModel):
    id: int
    sponsor_id: int
    sponsor: str
    anzahl: int
    preis_eur: int | None
    bis: date | None


class AssetAnsicht(BaseModel):
    id: int
    katalog_id: str
    name: str
    kategorie: str
    gegenleistung: str
    beschreibung: str | None
    anzahl: int
    belegt: int
    belegt_manuell: int
    frei: int
    preis_eur: int | None
    richtpreis: dict | None
    einnahmen_eur: int
    vergaben: list[VergabeAnsicht]


def _asset_ansichten(session: Session, verein: Verein) -> list[AssetAnsicht]:
    kat = katalog.nach_id()
    posten = session.exec(select(InventarPosten).where(InventarPosten.verein_id == verein.id)).all()
    ids = [p.id for p in posten]
    vergaben = session.exec(select(AssetVergabe).where(AssetVergabe.asset_id.in_(ids))).all() if ids else []
    namen = {s.id: s.firma for s in session.exec(select(Sponsor).where(Sponsor.verein_id == verein.id)).all()}
    ansichten = []
    for p in posten:
        e = kat.get(p.katalog_id)
        if not e:
            continue
        eigene = [v for v in vergaben if v.asset_id == p.id]
        belegt = belegte_einheiten(p, eigene)
        ansichten.append(AssetAnsicht(
            id=p.id, katalog_id=p.katalog_id, name=e["name"], kategorie=e["kategorie"],
            gegenleistung=e["gegenleistung"], beschreibung=p.beschreibung, anzahl=p.anzahl or 1,
            belegt=belegt, belegt_manuell=p.belegt_manuell or 0, frei=max(0, (p.anzahl or 1) - belegt), preis_eur=p.preis_eur,
            richtpreis=preis_band(p.katalog_id, verein),
            einnahmen_eur=sum(v.preis_eur or 0 for v in eigene),
            vergaben=[VergabeAnsicht(id=v.id, sponsor_id=v.sponsor_id, sponsor=namen.get(v.sponsor_id, "?"),
                                     anzahl=v.anzahl, preis_eur=v.preis_eur, bis=v.bis) for v in eigene],
        ))
    return sorted(ansichten, key=lambda a: (a.kategorie, a.name))


@router.get("/vereine/{verein_id}/assets", response_model=list[AssetAnsicht])
def assets(verein_id: int, session: Session = Depends(get_session)):
    return _asset_ansichten(session, _hole(session, Verein, verein_id, "Verein"))


class AssetNeu(BaseModel):
    katalog_id: str
    anzahl: int = 1
    preis_eur: int | None = None
    beschreibung: str | None = None


@router.post("/vereine/{verein_id}/assets", response_model=list[AssetAnsicht])
def asset_anlegen(verein_id: int, daten: AssetNeu, session: Session = Depends(get_session)):
    verein = _hole(session, Verein, verein_id, "Verein")
    if daten.katalog_id not in katalog.nach_id():
        raise HTTPException(422, "Unbekannte Katalog-ID")
    session.add(InventarPosten(verein_id=verein_id, **daten.model_dump()))
    session.commit()
    return _asset_ansichten(session, verein)


class AssetAenderung(BaseModel):
    anzahl: int | None = None
    belegt_manuell: int | None = None
    preis_eur: int | None = None
    beschreibung: str | None = None
    verfuegbar: bool | None = None


@router.patch("/assets/{asset_id}", response_model=list[AssetAnsicht])
def asset_aendern(asset_id: int, daten: AssetAenderung, session: Session = Depends(get_session)):
    p = _hole(session, InventarPosten, asset_id, "Asset")
    if daten.anzahl is not None and daten.anzahl < 1:
        raise HTTPException(422, "Anzahl muss mindestens 1 sein")
    _uebernehmen(p, daten)
    session.add(p)
    session.commit()
    return _asset_ansichten(session, _hole(session, Verein, p.verein_id, "Verein"))


@router.delete("/assets/{asset_id}", status_code=204)
def asset_loeschen(asset_id: int, session: Session = Depends(get_session)) -> None:
    p = _hole(session, InventarPosten, asset_id, "Asset")
    for v in session.exec(select(AssetVergabe).where(AssetVergabe.asset_id == asset_id)).all():
        session.delete(v)
    session.delete(p)
    session.commit()


class VergabeNeu(BaseModel):
    sponsor_id: int
    anzahl: int = 1
    preis_eur: int | None = None
    bis: date | None = None


@router.post("/assets/{asset_id}/vergaben", response_model=list[AssetAnsicht])
def vergabe_anlegen(asset_id: int, daten: VergabeNeu, session: Session = Depends(get_session)):
    p = _hole(session, InventarPosten, asset_id, "Asset")
    s = _hole(session, Sponsor, daten.sponsor_id, "Sponsor")
    if s.verein_id != p.verein_id:
        raise HTTPException(404, "Sponsor nicht gefunden")
    vorhanden = session.exec(select(AssetVergabe).where(AssetVergabe.asset_id == asset_id)).all()
    # Kurzform "komplett vergeben" aus dem Onboarding in echte Einheiten auflösen
    if not p.verfuegbar:
        p.verfuegbar = True
    if belegte_einheiten(p, vorhanden) + daten.anzahl > (p.anzahl or 1):
        raise HTTPException(422, "Nicht genug freie Einheiten – Anzahl des Assets erhöhen")
    session.add(AssetVergabe(asset_id=asset_id, **daten.model_dump()))
    session.add(p)
    _protokoll(session, p.verein_id, f"{daten.anzahl}× {katalog.nach_id()[p.katalog_id]['name']} vergeben",
               "vertrag", sponsor_id=s.id)
    session.commit()
    return _asset_ansichten(session, _hole(session, Verein, p.verein_id, "Verein"))


@router.delete("/vergaben/{vergabe_id}", status_code=204)
def vergabe_loeschen(vergabe_id: int, session: Session = Depends(get_session)) -> None:
    session.delete(_hole(session, AssetVergabe, vergabe_id, "Vergabe"))
    session.commit()
