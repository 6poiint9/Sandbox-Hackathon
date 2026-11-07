"""Sponsoring-Katalog (Quelle: docs/sponsoring-katalog.md)."""

import json
from functools import lru_cache
from pathlib import Path

KATALOG_DATEI = Path(__file__).with_name("katalog.json")


@lru_cache
def laden() -> list[dict]:
    return json.loads(KATALOG_DATEI.read_text(encoding="utf-8"))


def nach_id() -> dict[str, dict]:
    return {eintrag["id"]: eintrag for eintrag in laden()}
