"""Richtpreise und Potenzial. Bewusst einfache, transparente Regeln (CLAUDE.md).

Preise kommen immer aus dem Katalog × Faktoren, nie vom Sprachmodell.
"""

from app.data import katalog
from app.models import Verein

# Reihenfolge zählt: Spezielleres zuerst (Kreisliga vor Kreis…, Landesliga vor Liga).
SPIELKLASSE_FAKTOR: list[tuple[str, float]] = [
    ("kreisklasse", 0.6),
    ("kreisliga", 0.8),
    ("kreisstaffel", 0.6),
    ("bezirksliga", 1.0),
    ("landesliga", 1.3),
    ("verbandsliga", 1.6),
    ("oberliga", 1.6),
    ("regionalliga", 1.6),
]


def spielklasse_faktor(spielklasse: str | None) -> float:
    if not spielklasse:
        return 0.8
    klein = spielklasse.lower()
    if "jugend" in klein or "junior" in klein:
        return 0.7
    for muster, faktor in SPIELKLASSE_FAKTOR:
        if muster in klein:
            return faktor
    return 0.8


def zuschauer_faktor(zuschauer: int | None) -> float:
    if zuschauer is None:
        return 1.0
    if zuschauer < 50:
        return 0.8
    if zuschauer > 200:
        return 1.2
    return 1.0


def faktor(verein: Verein) -> float:
    return spielklasse_faktor(verein.spielklasse) * zuschauer_faktor(verein.zuschauer_schnitt)


def richtpreis(katalog_id: str, verein: Verein) -> dict | None:
    """Spanne für ein Paket in Euro, gerundet auf 50 €. None bei Sachleistungen."""
    eintrag = katalog.nach_id().get(katalog_id)
    if not eintrag or eintrag["preis_min"] is None:
        return None
    f = faktor(verein)

    def runden(x: float) -> int:
        return int(round(x * f / 50) * 50)

    return {
        "min": runden(eintrag["preis_min"]),
        "max": runden(eintrag["preis_max"]),
        "einheit": eintrag["einheit"],
        "quelle": eintrag["quelle"],
    }
