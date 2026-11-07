"""Richtpreise und Potenzial. Bewusst einfache, transparente Regeln (CLAUDE.md).

Preise kommen immer aus dem Katalog × Faktoren, nie vom Sprachmodell.
"""

from pydantic import BaseModel

from app.data import katalog
from app.models import AssetVergabe, InventarPosten, Sponsor, Verein

# Annahmen für Pakete, die nicht pro Saison bepreist sind. Werden in der UI angezeigt.
HEIMSPIELE = 12
BUSINESSCLUB_MITGLIEDER = 5

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


def _band(preis: dict, menge: int = 1) -> tuple[int, int]:
    """Mittleres Band (25–75 %) einer Katalogspanne, gerundet auf 50 €."""
    breite = preis["max"] - preis["min"]
    unten = int(round((preis["min"] + 0.25 * breite) * menge / 50) * 50)
    oben = int(round((preis["min"] + 0.75 * breite) * menge / 50) * 50)
    return unten, oben


def preis_band(katalog_id: str, verein: Verein) -> dict | None:
    """Richtpreis eines Pakets wie in der Potenzialanalyse (inkl. Menge)."""
    preis = richtpreis(katalog_id, verein)
    if not preis:
        return None
    menge, _ = _menge(katalog_id, preis["einheit"], verein)
    unten, oben = _band(preis, menge)
    return {"min": unten, "max": oben}


class Paket(BaseModel):
    katalog_id: str
    name: str
    kategorie: str
    min: int
    max: int
    menge: int = 1
    einheiten_frei: int = 1
    annahme: str | None = None
    quelle: str  # "findasponsor" oder "schaetzung"
    eigener_preis: bool = False


# Ohne gepflegtes Inventar zählen nur Pakete, die fast jeder Verein hat (wie im Onboarding vorausgewählt).
STANDARD_PAKETE = ("bande", "website", "social_media", "spieltag", "vereinsfest", "trainingsanzug", "turnier")

# Marktwert eines Vereins: Sponsoring je Mitglied und Saison. Kreisligist mit rund 300 Mitgliedern
# erreicht 3.000–8.000 € (motivation4teams, Ratgeber Vereinssponsoring) ≈ 10–27 € je Mitglied;
# bundesweit ~8.400 € je Verein bei ~310 Mitgliedern (VSA/DSHS 2026; DOSB-Bestand) ≈ 27 €.
EURO_JE_MITGLIED = (10, 27)
# Wie weit die Summe der freien Pakete über dem Marktwert liegen darf (gutes Angebot, aktive Ansprache).
LUFT_NACH_OBEN = 1.25


def marktwert(verein: Verein) -> tuple[int, int] | None:
    """Übliches Sponsoring pro Saison für diesen Verein, skaliert nach Spielklasse. None ohne Mitglieder."""
    if not verein.mitglieder:
        return None
    f = spielklasse_faktor(verein.spielklasse)
    unten, oben = (round(verein.mitglieder * e * f / 100) * 100 for e in EURO_JE_MITGLIED)
    return max(unten, 100), max(oben, 200)


class Potenzial(BaseModel):
    spanne_min: int  # realistisch: Summe der freien Pakete, begrenzt durch den Marktwert
    spanne_max: int
    theoretisch_min: int = 0  # wenn jedes freie Paket verkauft würde
    theoretisch_max: int = 0
    marktwert_min: int | None = None
    marktwert_max: int | None = None
    freie_pakete: list[Paket]
    sachleistungen: list[str]
    vergebene_pakete: list[dict]
    bestand_eur: int
    bestand_sponsoren: int
    luecken: list[dict]
    betriebe_im_umkreis: int | None
    annahmen: list[str]
    hinweis: str


def _menge(katalog_id: str, einheit: str, verein: Verein) -> tuple[int, str | None]:
    if einheit == "je_spiel":
        return HEIMSPIELE, f"{HEIMSPIELE} Heimspiele pro Saison"
    if einheit == "je_mitglied":
        return BUSINESSCLUB_MITGLIEDER, f"{BUSINESSCLUB_MITGLIEDER} Mitglieder im Sponsorenkreis"
    if einheit == "je_satz" and verein.jugend_anzahl:
        n = verein.jugend_anzahl
        return n, f"{n} Jugendmannschaft(en) laut Profil"
    if einheit == "je_satz":
        jugend = [
            m for m in verein.mannschaften
            if any(w in (m.get("name") or "").lower() for w in ("jugend", "junior", "u1", "u2", "bambini"))
        ]
        n = max(1, len(jugend))
        return n, f"{n} Jugendmannschaft(en) laut Profil"
    return 1, None


def belegte_einheiten(p: InventarPosten, vergaben: list[AssetVergabe]) -> int:
    if not p.verfuegbar or p.vergeben_an:
        return p.anzahl or 1
    zugeordnet = sum(v.anzahl for v in vergaben if v.asset_id == p.id)
    return min(p.anzahl or 1, zugeordnet + (p.belegt_manuell or 0))


def berechnen(
    verein: Verein,
    inventar: list[InventarPosten],
    sponsoren: list[Sponsor],
    vergaben: list[AssetVergabe] | None = None,
) -> Potenzial:
    """Ungenutztes Potenzial = Summe der freien, bepreisten Pakete.

    Die Spanne nutzt das mittlere Band (25–75 %) jeder Katalogspanne, damit die
    Zahl nicht künstlich breit wird. Eigene Preise des Vereins haben Vorrang.
    """
    kat = katalog.nach_id()
    namen = {s.id: s.firma for s in sponsoren}
    gepflegt = bool(inventar)
    posten = inventar or [InventarPosten(verein_id=verein.id or 0, katalog_id=k) for k in STANDARD_PAKETE if k in kat]

    freie: list[Paket] = []
    sach: list[str] = []
    vergeben: list[dict] = []
    annahmen: set[str] = set()
    for p in posten:
        e = kat.get(p.katalog_id)
        if not e:
            continue
        belegt = belegte_einheiten(p, vergaben or [])
        frei = (p.anzahl or 1) - belegt
        if frei <= 0:
            vergeben.append({"katalog_id": p.katalog_id, "name": e["name"], "sponsor": namen.get(p.vergeben_an)})
            continue
        if frei > 1:
            annahmen.add(f"{e['name']}: {frei} von {p.anzahl} Einheiten frei")
        if p.preis_eur:
            freie.append(Paket(katalog_id=p.katalog_id, name=e["name"], kategorie=e["kategorie"],
                               min=p.preis_eur * frei, max=p.preis_eur * frei, quelle="verein",
                               eigener_preis=True, einheiten_frei=frei))
            continue
        preis = richtpreis(p.katalog_id, verein)
        if not preis:
            sach.append(e["name"])
            continue
        menge, annahme = _menge(p.katalog_id, e["einheit"], verein)
        if annahme:
            annahmen.add(annahme)
        unten, oben = _band(preis, menge)
        freie.append(Paket(katalog_id=p.katalog_id, name=e["name"], kategorie=e["kategorie"],
                           min=unten * frei, max=oben * frei, menge=menge, annahme=annahme,
                           quelle=preis["quelle"], einheiten_frei=frei))

    freie.sort(key=lambda x: -x.max)
    annahmen.add(
        f"Faktor {faktor(verein):.2f} aus Spielklasse „{verein.spielklasse or 'unbekannt'}“ "
        f"und {verein.zuschauer_schnitt or 'unbekannt'} Zuschauern"
    )
    if not gepflegt:
        annahmen.add("Kein Angebot gepflegt: nur übliche Standardpakete gezählt")

    theo_min, theo_max = sum(x.min for x in freie), sum(x.max for x in freie)
    spanne_min, spanne_max = theo_min, theo_max
    mw = marktwert(verein)
    if mw:
        deckel = int(round(mw[1] * LUFT_NACH_OBEN / 100) * 100)
        spanne_max = min(theo_max, deckel)
        spanne_min = min(theo_min, mw[0], spanne_max)
        if theo_max > deckel:
            annahmen.add(
                f"Begrenzt auf den Marktwert eures Vereins: {verein.mitglieder} Mitglieder × "
                f"{EURO_JE_MITGLIED[0]}–{EURO_JE_MITGLIED[1]} € × Spielklasse = {mw[0]}–{mw[1]} € "
                f"(+{round((LUFT_NACH_OBEN - 1) * 100)} % Luft)"
            )

    return Potenzial(
        spanne_min=spanne_min,
        spanne_max=spanne_max,
        theoretisch_min=theo_min,
        theoretisch_max=theo_max,
        marktwert_min=mw[0] if mw else None,
        marktwert_max=mw[1] if mw else None,
        freie_pakete=freie,
        sachleistungen=sach,
        vergebene_pakete=vergeben,
        bestand_eur=sum(s.betrag_eur or 0 for s in sponsoren),
        bestand_sponsoren=len(sponsoren),
        luecken=verein.luecken or [],
        betriebe_im_umkreis=verein.betriebe_im_umkreis,
        annahmen=sorted(annahmen),
        hinweis="Richtwerte: Marktwerte (findasponsor) und Schätzungen, skaliert nach Spielklasse "
        "und Zuschauern. Keine Garantie; eigene Preise des Vereins haben Vorrang.",
    )
