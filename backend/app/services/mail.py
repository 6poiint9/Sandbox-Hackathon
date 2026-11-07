"""E-Mail-Benachrichtigung, wenn die Potenzialanalyse fertig ist (SMTP, optional)."""

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def verfuegbar() -> bool:
    s = get_settings()
    return bool(s.smtp_host and s.smtp_absender)


def senden(an: str, betreff: str, text: str) -> bool:
    """Gibt True zurück, wenn die Mail raus ist. Fehler werden geloggt, nie geworfen."""
    s = get_settings()
    if not verfuegbar():
        return False
    nachricht = EmailMessage()
    nachricht["From"] = s.smtp_absender
    nachricht["To"] = an
    nachricht["Subject"] = betreff
    nachricht.set_content(text)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as server:
            server.starttls()
            if s.smtp_benutzer:
                server.login(s.smtp_benutzer, s.smtp_passwort)
            server.send_message(nachricht)
        return True
    except (smtplib.SMTPException, OSError) as e:
        logger.warning("E-Mail an %s fehlgeschlagen: %s", an, e)
        return False


def analyse_fertig_text(verein_name: str, link: str, spanne: tuple[int, int], top: list[tuple[str, int, str]]) -> str:
    zeilen = [
        "Hallo,",
        "",
        f"die Potenzialanalyse für {verein_name} ist fertig.",
        "",
        f"Ungenutztes Sponsoring-Potenzial: {spanne[0]:,} – {spanne[1]:,} € pro Saison (Richtwert)".replace(",", "."),
        "",
        "Eure besten Kandidaten:",
        *[f"- {name} ({branche}), Score {score}" for name, score, branche in top],
        "",
        f"Zur Analyse mit Gründen, Quellen und fertigen Briefen: {link}",
        "",
        "Viele Grüße",
        "Sponsorenkompass",
    ]
    return "\n".join(zeilen)
