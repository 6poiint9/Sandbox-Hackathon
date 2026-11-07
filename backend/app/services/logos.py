"""Sponsoren aus Logos erkennen.

Viele Vereine zeigen Sponsoren nur als Logo (Bild mit Link), ohne Text. Darum:
1. Sponsorenseite(n) der Vereinsdomain finden und das HTML laden.
2. Alle Bilder mit Alternativtext und Link-Ziel einsammeln.
3. Bilder laden und Gemini (multimodal) lesen lassen: Firmenname je Logo,
   Behörden/Förderprogramme/Siegel/eigenes Vereinslogo aussortieren.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, Field

from app.providers.cache import zwischengespeichert
from app.providers.llm import GeminiModell

logger = logging.getLogger(__name__)

UA = {"User-Agent": "Mozilla/5.0 (compatible; Sponsorenkompass/0.1; Hackathon-Prototyp)"}
PFADE = ["sponsoren", "sponsoren/", "partner", "unsere-sponsoren", "sponsoring", "werbepartner", "foerderer"]
LINK_MUSTER = re.compile(r"sponsor|partner|f(oe|ö)rder|werbe", re.I)
MAX_BILDER = 40
BILDTYPEN = {"image/png", "image/jpeg", "image/webp"}


class LogoFund(BaseModel):
    bild: str
    alt: str | None = None
    link: str | None = None


class _Sammler(HTMLParser):
    def __init__(self, basis: str) -> None:
        super().__init__()
        self.basis = basis
        self.link: str | None = None
        self.bilder: list[LogoFund] = []
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a":
            self.link = _url(self.basis, a.get("href"))
            if self.link:
                self.links.append(self.link)
        elif tag == "img":
            src = _url(self.basis, a.get("data-src") or a.get("data-lazy-src") or a.get("src"))
            if src:
                self.bilder.append(LogoFund(bild=src, alt=_text(a.get("alt") or a.get("title")), link=self.link))

    def handle_endtag(self, tag):
        if tag == "a":
            self.link = None


def _text(t: str | None) -> str | None:
    return re.sub(r"\s+", "", t) if t and "." in t and " " not in t.strip() else (re.sub(r"\s+", " ", t).strip() if t else None)


def _url(basis: str, roh: str | None) -> str | None:
    if not roh:
        return None
    roh = re.sub(r"\s+", "", roh)  # WordPress-Seiten enthalten teils Umbrüche in URLs
    if roh.startswith(("data:", "javascript:", "mailto:", "tel:", "#")):
        return None
    if roh.startswith("http:") and not roh.startswith("http://"):
        roh = "http://" + roh[5:]
    return urljoin(basis, roh)


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _html(url: str) -> str | None:
    try:
        r = httpx.get(url, headers=UA, timeout=15, follow_redirects=True)
        if r.status_code == 200 and "html" in r.headers.get("content-type", ""):
            return r.text
    except httpx.HTTPError:
        pass
    return None


def sponsorenseiten(website: str, hinweise: list[str] | None = None) -> list[str]:
    """Kandidaten für Sponsorenseiten: verlinkt auf der Startseite, bekannte Pfade, Hinweise aus Exa."""
    start = website if "://" in website else f"https://{website}"
    domain = _domain(start)
    seiten: list[str] = []
    html = _html(start)
    if html:
        s = _Sammler(start)
        s.feed(html)
        seiten += [l for l in s.links if _domain(l) == domain and LINK_MUSTER.search(urlparse(l).path)]
    seiten += [u for u in (hinweise or []) if _domain(u) == domain and LINK_MUSTER.search(urlparse(u).path)]
    seiten += [urljoin(start if start.endswith("/") else start + "/", p) for p in PFADE]
    eindeutig = list(dict.fromkeys(seiten))
    # "category"-Archivseiten sind meist News-Listen ohne Logos – nach hinten
    return sorted(eindeutig, key=lambda u: ("category" in u, len(u)))[:8]


def logos_sammeln(website: str, hinweise: list[str] | None = None) -> tuple[list[LogoFund], str | None]:
    domain = _domain(website if "://" in website else f"https://{website}")
    for seite in sponsorenseiten(website, hinweise):
        html = _html(seite)
        if not html:
            continue
        s = _Sammler(seite)
        s.feed(html)
        # Logos verlinken typischerweise auf fremde Domains
        externe = [b for b in s.bilder if b.link and _domain(b.link) != domain]
        if len(externe) >= 3:
            eindeutig = {b.bild: b for b in s.bilder}
            return list(eindeutig.values())[:MAX_BILDER], seite
    return [], None


def _bild_laden(url: str) -> tuple[bytes, str] | None:
    try:
        r = httpx.get(url, headers=UA, timeout=10, follow_redirects=True)
    except httpx.HTTPError:
        return None
    typ = r.headers.get("content-type", "").split(";")[0].strip()
    if r.status_code != 200 or typ not in BILDTYPEN or not (1500 < len(r.content) < 3_000_000):
        return None
    return r.content, typ


class LogoFirma(BaseModel):
    bild_nr: int
    firma: str = Field(description="Firmenname wie auf dem Logo, z. B. 'Ketterer Maschinenbau GmbH'")
    ist_sponsor: bool = Field(description="false für Vereinslogo, Verband, Behörde/Stadt, Förderprogramm, Siegel, QR-Code, Social Media")


class LogoAntwort(BaseModel):
    logos: list[LogoFirma]


SYSTEM = """Du erkennst Sponsoren eines Sportvereins anhand der Logos auf seiner Sponsorenseite.
Für jedes Bild: Lies den Firmennamen vom Logo. Nutze Alternativtext und Link-Ziel als Hilfe, aber das Logo hat Vorrang.
ist_sponsor = false für: das Logo des Vereins selbst, Sportverbände, Städte/Behörden, Förderprogramme, Siegel, QR-Codes, Fotos ohne Firma.
Nichts erfinden: Ist kein Name lesbar und kein Link vorhanden, lass das Bild weg."""


class ErkannterLogoSponsor(BaseModel):
    firma: str
    website: str | None
    logo_url: str


def sponsoren_aus_logos(website: str, hinweise: list[str] | None = None) -> tuple[list[ErkannterLogoSponsor], str | None]:
    """Gibt (Sponsoren, Sponsorenseite) zurück. Fehler führen zu einer leeren Liste."""

    def holen() -> dict:
        funde, seite = logos_sammeln(website, hinweise)
        if not funde:
            return {"sponsoren": [], "seite": None}
        with ThreadPoolExecutor(max_workers=8) as pool:
            geladen = list(pool.map(lambda f: _bild_laden(f.bild), funde))
        bilder = [(f, g) for f, g in zip(funde, geladen) if g]
        if not bilder:
            return {"sponsoren": [], "seite": seite}

        from google.genai import types

        teile: list = []
        for i, (f, (daten, typ)) in enumerate(bilder, 1):
            teile.append(f"Bild {i}: Alternativtext={f.alt or '-'} | Link={f.link or '-'}")
            teile.append(types.Part.from_bytes(data=daten, mime_type=typ))
        teile.append("Gib für jedes Bild mit lesbarer Firma bild_nr, firma und ist_sponsor zurück.")

        modell = GeminiModell(_modellname())
        antwort = modell._client_holen().models.generate_content(
            model=modell.name,
            contents=teile,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM,
                response_mime_type="application/json",
                response_schema=LogoAntwort,
                temperature=0.1,
            ),
        )
        erg = LogoAntwort.model_validate_json(antwort.text or '{"logos": []}')
        sponsoren = []
        for l in erg.logos:
            if not l.ist_sponsor or not (1 <= l.bild_nr <= len(bilder)):
                continue
            f = bilder[l.bild_nr - 1][0]
            sponsoren.append({"firma": l.firma.strip(), "website": f.link, "logo_url": f.bild})
        return {"sponsoren": sponsoren, "seite": seite}

    try:
        roh = zwischengespeichert("logos", holen, website=_domain(website if "://" in website else f"https://{website}"))
    except Exception as e:  # Logo-Erkennung ist ein Bonus, nie ein Abbruchgrund
        logger.warning("Logo-Erkennung fehlgeschlagen: %s", e)
        return [], None
    return [ErkannterLogoSponsor(**s) for s in roh["sponsoren"]], roh["seite"]


def _modellname() -> str:
    from app.config import get_settings

    return get_settings().llm_analyse_model
