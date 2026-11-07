"""Datenmodell. Begriffe sind fest (siehe CLAUDE.md), nicht umbenennen."""

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class VereinBasis(SQLModel):
    name: str
    website: str | None = None
    ort: str
    sportstaette: str | None = None  # Name + Adresse, Mittelpunkt der Umkreissuche
    lat: float | None = None
    lon: float | None = None
    sportarten: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    mannschaften: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    spielklasse: str | None = None
    mitglieder: int | None = None
    zuschauer_schnitt: int | None = None
    zielgruppen: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    reichweite: dict = Field(default_factory=dict, sa_column=Column(JSON))
    veranstaltungen: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    radius_km: float = 15
    ziel_eur: int | None = None
    # Ergebnis der letzten Umkreissuche: [{"branche": ..., "betriebe": n}]
    luecken: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    betriebe_im_umkreis: int | None = None
    # Hintergrundauftrag Umkreissuche + Recherche
    suche_status: str = "offen"  # offen, laeuft, fertig, fehler
    suche_fehler: str | None = None
    benachrichtigung_email: str | None = None


class Verein(VereinBasis, table=True):
    id: int | None = Field(default=None, primary_key=True)
    konto_id: int | None = Field(default=None, index=True)  # None = ohne Konto angelegt
    # Gast ohne Konto: SHA-256 des Gast-Cookies. Nie ausliefern (exclude), nur vergleichen.
    gast_hash: str | None = Field(default=None, index=True, exclude=True)


class InventarPosten(SQLModel, table=True):
    """Ein Sponsoring-Asset des Vereins, z. B. "Bandenwerbung" mit 12 Banden."""

    id: int | None = Field(default=None, primary_key=True)
    verein_id: int = Field(foreign_key="verein.id", index=True)
    katalog_id: str
    verfuegbar: bool = True  # False = komplett vergeben (Kurzform aus dem Onboarding)
    vergeben_an: int | None = Field(default=None, foreign_key="sponsor.id")
    preis_eur: int | None = None  # eigener Preis je Einheit und Saison
    anzahl: int = 1  # Einheiten, z. B. Banden oder Trikotsätze
    beschreibung: str | None = None


class AssetVergabe(SQLModel, table=True):
    """Welcher Sponsor hat wie viele Einheiten eines Assets, zu welchem Preis, bis wann."""

    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="inventarposten.id", index=True)
    sponsor_id: int = Field(foreign_key="sponsor.id", index=True)
    anzahl: int = 1
    preis_eur: int | None = None
    bis: date | None = None


class SponsorBasis(SQLModel):
    firma: str
    website: str | None = None
    gegenleistung: str | None = None  # katalog_id, falls zuordenbar
    gegenleistung_text: str | None = None  # Originaltext aus Website oder CSV
    betrag_eur: int | None = None
    laufzeit_bis: date | None = None
    ansprechpartner: str | None = None
    email: str | None = None
    telefon: str | None = None
    status: str = "aktiv"  # aktiv, verlaengerung, beendet
    naechster_schritt: str | None = None
    wiedervorlage: date | None = None
    logo_url: str | None = None
    notiz: str | None = None


class Sponsor(SponsorBasis, table=True):
    id: int | None = Field(default=None, primary_key=True)
    verein_id: int = Field(foreign_key="verein.id", index=True)


class Unternehmen(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    osm_id: str = Field(index=True, unique=True)  # z. B. "node/123"
    name: str
    branche: str  # unsere Branchenbezeichnung, passend zu katalog.zielbranchen
    osm_typ: str | None = None  # Original-Tag, z. B. "shop=bakery"
    adresse: str | None = None
    lat: float
    lon: float
    website: str | None = None


KANDIDAT_STATUS = ("neu", "kontaktiert", "termin", "zusage", "absage")


class Kandidat(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    verein_id: int = Field(foreign_key="verein.id", index=True)
    unternehmen_id: int = Field(foreign_key="unternehmen.id")
    entfernung_km: float
    vorfilter_score: int
    vorfilter_gruende: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    score: int | None = None
    sicherheit: str | None = None
    gruende: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    paket_empfehlung: dict = Field(default_factory=dict, sa_column=Column(JSON))
    zusammenfassung: str | None = None
    quellen: list[dict] = Field(default_factory=list, sa_column=Column(JSON))  # [{url, titel}]
    recherche_status: str = "offen"  # offen, wartet, laeuft, fertig, fehler
    recherche_fehler: str | None = None
    status: str = "neu"
    # CRM
    ansprechpartner: str | None = None
    email: str | None = None
    telefon: str | None = None
    naechster_schritt: str | None = None
    wiedervorlage: date | None = None
    notiz: str | None = None
    sponsor_id: int | None = None  # nach Zusage übernommen als Sponsor


class Ansprache(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    kandidat_id: int = Field(foreign_key="kandidat.id", index=True, unique=True)
    brief: str
    leitfaden: str
    email_betreff: str
    email_text: str


AKTIVITAET_ARTEN = ("notiz", "anruf", "brief", "email", "treffen", "status", "vertrag")


class Aktivitaet(SQLModel, table=True):
    """CRM-Verlauf: was ist mit einem Sponsor oder Kandidaten passiert."""

    id: int | None = Field(default=None, primary_key=True)
    verein_id: int = Field(foreign_key="verein.id", index=True)
    sponsor_id: int | None = Field(default=None, index=True)
    kandidat_id: int | None = Field(default=None, index=True)
    art: str = "notiz"
    text: str
    zeitpunkt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Interessent(SQLModel, table=True):
    """Anmeldung über die Landingpage (Warteliste / Pilotverein)."""

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    verein: str | None = None
    rolle: str | None = None  # z. B. Vorstand, Kassenwart, Sponsoring-Verantwortliche
    nachricht: str | None = None
    pilot: bool = False
    zeitpunkt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Konto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str | None = None
    passwort_hash: str
    abo: bool = False  # Demo-Abo: schaltet alle Kandidaten frei (keine echte Zahlung)
    erstellt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Sitzung(SQLModel, table=True):
    token_hash: str = Field(primary_key=True)  # sha256 des Tokens, das Token selbst wird nie gespeichert
    konto_id: int = Field(foreign_key="konto.id", index=True)
    erstellt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ablauf: datetime | None = None
    letzter_zugriff: datetime | None = None
