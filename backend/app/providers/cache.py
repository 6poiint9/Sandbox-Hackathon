"""JSON-Cache für externe Aufrufe.

- Normaler Cache: backend/cache/<schluessel>.json (nicht im Repo)
- Demo-Cache:     backend/cache/demo/<schluessel>.json (im Repo, eingefrorene Demo-Daten)

Im DEMO_MODE wird ausschließlich der Demo-Cache gelesen; fehlt ein Eintrag,
gibt es einen klaren Fehler statt eines externen Aufrufs.
"""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.config import get_settings


class DemoDatenFehlen(RuntimeError):
    """Im DEMO_MODE wurde ein Aufruf angefragt, der nicht eingefroren ist."""


def schluessel(bereich: str, **parameter: Any) -> str:
    roh = json.dumps({"bereich": bereich, **parameter}, sort_keys=True, ensure_ascii=False)
    return f"{bereich}-{hashlib.sha256(roh.encode('utf-8')).hexdigest()[:24]}"


def _lesen(pfad: Path) -> Any | None:
    if pfad.exists():
        return json.loads(pfad.read_text(encoding="utf-8"))
    return None


def zwischengespeichert(bereich: str, holen: Callable[[], Any], **parameter: Any) -> Any:
    """Gibt das gecachte Ergebnis zurück oder ruft `holen()` auf und speichert es."""
    settings = get_settings()
    name = schluessel(bereich, **parameter) + ".json"
    demo_pfad = settings.cache_dir / "demo" / name
    cache_pfad = settings.cache_dir / name

    demo = _lesen(demo_pfad)
    if demo is not None:
        return demo
    if settings.demo_mode:
        raise DemoDatenFehlen(f"Keine Demo-Daten für {bereich} {parameter}")

    vorhanden = _lesen(cache_pfad)
    if vorhanden is not None:
        return vorhanden

    ergebnis = holen()
    cache_pfad.parent.mkdir(parents=True, exist_ok=True)
    cache_pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    return ergebnis
