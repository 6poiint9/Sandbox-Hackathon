"""Datenmodell. Begriffe sind fest (siehe CLAUDE.md), nicht umbenennen."""

from datetime import date

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class VereinBasis(SQLModel):
    name: str
    website: str | None = None
    ort: str
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


class Verein(VereinBasis, table=True):
    id: int | None = Field(default=None, primary_key=True)


class InventarPosten(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    verein_id: int = Field(foreign_key="verein.id", index=True)
    katalog_id: str
    verfuegbar: bool = True
    vergeben_an: int | None = Field(default=None, foreign_key="sponsor.id")
    preis_eur: int | None = None


class SponsorBasis(SQLModel):
    firma: str
    website: str | None = None
    gegenleistung: str | None = None  # katalog_id, falls zuordenbar
    gegenleistung_text: str | None = None  # Originaltext aus Website oder CSV
    betrag_eur: int | None = None
    laufzeit_bis: date | None = None
    ansprechpartner: str | None = None
    notiz: str | None = None


class Sponsor(SponsorBasis, table=True):
    id: int | None = Field(default=None, primary_key=True)
    verein_id: int = Field(foreign_key="verein.id", index=True)
