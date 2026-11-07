"""Datenbank: SQLModel auf SQLite.

`init_db` legt fehlende Tabellen an und ergänzt fehlende Spalten (einfache
Migration für die Hackathon-Datenbank, keine Daten gehen verloren).
"""

from collections.abc import Iterator

from sqlalchemy import JSON, inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

engine = create_engine(
    get_settings().database_url, connect_args={"check_same_thread": False}
)


def _spalten_ergaenzen(eng) -> None:
    pruefer = inspect(eng)
    with eng.begin() as verbindung:
        for tabelle in SQLModel.metadata.sorted_tables:
            if not pruefer.has_table(tabelle.name):
                continue
            vorhanden = {s["name"] for s in pruefer.get_columns(tabelle.name)}
            for spalte in tabelle.columns:
                if spalte.name in vorhanden:
                    continue
                typ = spalte.type.compile(dialect=eng.dialect)
                standard = ""
                if isinstance(spalte.type, JSON):
                    standard = " DEFAULT '{}'" if "dict" in str(spalte.info) else " DEFAULT '[]'"
                elif spalte.default is not None and getattr(spalte.default, "is_scalar", False):
                    wert = spalte.default.arg
                    standard = f" DEFAULT {int(wert) if isinstance(wert, bool) else repr(wert)}"
                verbindung.execute(text(f'ALTER TABLE "{tabelle.name}" ADD COLUMN "{spalte.name}" {typ}{standard}'))


def init_db(eng=None) -> None:
    eng = eng or engine
    SQLModel.metadata.create_all(eng)
    _spalten_ergaenzen(eng)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
