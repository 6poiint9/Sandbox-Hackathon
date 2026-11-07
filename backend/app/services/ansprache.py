"""Ansprache: Brief, Telefonleitfaden und E-Mail für NACH dem Erstkontakt.

Kein Versand aus dem Tool. Brief und Anruf zuerst, weil unaufgeforderte
E-Mails auch zwischen Unternehmen als Werbung gelten können.
"""

from pydantic import BaseModel, Field

from app.models import Kandidat, Unternehmen, Verein
from app.providers.llm import Sprachmodell

SYSTEM = """Du schreibst für einen ehrenamtlichen Vereinsvorstand eine persönliche Sponsoring-Anfrage an ein lokales Unternehmen.
Regeln:
- Bezug nehmen auf die genannten Gründe (konkret, z. B. bisheriges Engagement oder Ausbildung), keine Floskeln, kein Massenbrief-Ton.
- Nur Fakten aus den Angaben verwenden. Keine Namen von Ansprechpartnern erfinden: Anrede "Sehr geehrte Damen und Herren" oder an die Geschäftsleitung.
- Konkretes Angebot mit dem empfohlenen Paket und dem Richtpreis als Spanne nennen, offen für Gespräch.
- Nutzen für das Unternehmen in den Vordergrund (Sichtbarkeit vor Ort, Nachwuchs, Kundschaft), nicht Bitte um Geld.
- Platzhalter in eckigen Klammern für Absenderdaten: [Name], [Funktion], [Telefon], [E-Mail].
- Brief: höchstens 200 Wörter. Leitfaden: Stichpunkte für ein 5-Minuten-Telefonat inkl. Einwände.
- E-Mail ist das Follow-up NACH einem Telefonat oder Treffen ("wie besprochen ..."), keine Kaltakquise.
- Deutsch, freundlich, auf Augenhöhe."""


class AnspracheText(BaseModel):
    brief: str = Field(description="Kompletter Brief inkl. Anrede und Grußformel")
    leitfaden: str = Field(description="Telefonleitfaden als Stichpunkte, Zeilen beginnen mit '- '")
    email_betreff: str
    email_text: str = Field(description="Follow-up-E-Mail nach dem Erstkontakt")


def prompt_bauen(verein: Verein, k: Kandidat, u: Unternehmen) -> str:
    pe = k.paket_empfehlung or {}
    preis = pe.get("preis_eur")
    preis_text = f"{preis['min']}–{preis['max']} € pro Saison (Richtwert)" if preis else "nach Absprache"
    gruende = "\n".join(f"- {g['text']}" for g in k.gruende) or "- (keine belegten Gründe)"
    mannschaften = ", ".join(
        f"{m.get('name')} ({m.get('spielklasse')})" for m in verein.mannschaften[:5] if m.get("name")
    )
    return f"""VEREIN: {verein.name}, {verein.ort}
Sportarten: {", ".join(verein.sportarten) or "-"} | Mannschaften: {mannschaften or "-"}
Veranstaltungen: {", ".join(verein.veranstaltungen) or "-"}
Mitglieder: {verein.mitglieder or "unbekannt"} | Zuschauer je Heimspiel: {verein.zuschauer_schnitt or "unbekannt"}

UNTERNEHMEN: {u.name} ({u.branche}), {u.adresse or verein.ort}, {k.entfernung_km:.1f} km vom Verein
Steckbrief: {k.zusammenfassung or "-"}

GRÜNDE (belegt):
{gruende}

EMPFOHLENES PAKET: {", ".join(pe.get("namen", [])) or "-"} – {preis_text}
Begründung: {pe.get("begruendung") or "-"}

Schreibe Brief, Telefonleitfaden und Follow-up-E-Mail."""


def erzeugen(modell: Sprachmodell, verein: Verein, k: Kandidat, u: Unternehmen) -> AnspracheText:
    return modell.json(SYSTEM, prompt_bauen(verein, k, u), AnspracheText)
