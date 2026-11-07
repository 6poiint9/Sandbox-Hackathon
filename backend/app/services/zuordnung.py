"""Freitext einer Gegenleistung ("Bandenwerbung Hauptplatz") -> Katalog-ID.

Bewusst einfache Schlagwortregeln statt KI: nachvollziehbar und testbar.
"""

import re

from app.data import katalog

# Reihenfolge zählt: Spezielleres zuerst.
REGELN: list[tuple[str, str]] = [
    (r"trikot.*(brust|haupt)|brustwerbung|hauptsponsor", "trikot_brust"),
    (r"trikot.*(jugend|junior|kinder)|jugendtrikot", "trikot_jugend"),
    (r"trikot.*(rück|ruck|ärmel|arm|hose)", "trikot_ruecken"),
    (r"trikot", "trikot_brust"),
    (r"trainingsanz|aufwärm|teamwear|polo|jacke", "trainingsanzug"),
    (r"bande|banner.*platz|platzbanner", "bande"),
    (r"halle", "banner_halle"),
    (r"anzeigetafel|uhr|tafel", "anzeigetafel"),
    (r"namensrecht|arena|stadion.*name|sportpark", "namensrecht_platz"),
    (r"vereinsheim|clubhaus|getränkekarte", "vereinsheim"),
    (r"bus|fahrzeug|anhänger", "vereinsbus"),
    (r"ball|ausrüst|material|tor", "ausruestung"),
    (r"social|instagram|facebook|tiktok", "social_media"),
    (r"stadionheft|vereinszeitung|anzeige|heft|magazin", "stadionheft"),
    (r"newsletter", "newsletter"),
    (r"durchsage", "durchsage"),
    (r"spieltag|matchball|heimspiel", "spieltag"),
    (r"turnier|cup", "turnier"),
    (r"fest|stand", "vereinsfest"),
    (r"azubi|ausbildung|praktik|recruit", "azubi"),
    (r"pate|patenschaft", "patenschaft"),
    (r"firmenlauf|mitarbeiter|teamevent", "mitarbeiter_events"),
    (r"rabatt|vorteil|gutschein", "mitgliedervorteil"),
    (r"business|vip|sponsorenkreis|sponsorenpool|förderkreis|freunde der", "businessclub"),
    (r"sach|getränke|druck|reparatur", "sachsponsoring"),
    (r"website|homepage|logo.*seite|online", "website"),
]


def katalog_id(text: str | None) -> str | None:
    if not text:
        return None
    klein = text.strip().lower()
    if klein in katalog.nach_id():
        return klein
    for muster, kid in REGELN:
        if re.search(muster, klein):
            return kid
    return None
