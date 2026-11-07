"""Austauschbares Sprachmodell. Umsetzung: Gemini (Vertex AI oder API-Key).

Jede Antwort ist JSON nach einem Pydantic-Schema, wird validiert und gecacht.
Bei ungültiger Antwort genau ein zweiter Versuch, dann ein klarer Fehler.
"""

import json
import time
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.providers.cache import zwischengespeichert

T = TypeVar("T", bound=BaseModel)


class SprachmodellFehler(RuntimeError):
    pass


class Sprachmodell(Protocol):
    name: str

    def json(self, system: str, prompt: str, schema: type[T]) -> T: ...


class GeminiModell:
    def __init__(self, modell: str, client=None) -> None:
        self.name = modell
        self._client = client

    def _client_holen(self):
        if self._client is None:
            from google import genai

            s = get_settings()
            if s.google_genai_use_vertexai and s.google_api_key:
                self._client = genai.Client(vertexai=True, api_key=s.google_api_key)  # Express-Modus
            elif s.google_genai_use_vertexai:
                if not s.google_cloud_project:
                    raise SprachmodellFehler("GOOGLE_CLOUD_PROJECT oder GOOGLE_API_KEY fehlt in .env")
                self._client = genai.Client(
                    vertexai=True, project=s.google_cloud_project, location=s.google_cloud_location
                )
            elif s.gemini_api_key:
                self._client = genai.Client(api_key=s.gemini_api_key)
            else:
                raise SprachmodellFehler(
                    "Kein Gemini-Zugang: GOOGLE_GENAI_USE_VERTEXAI=True oder GEMINI_API_KEY in .env"
                )
        return self._client

    def _aufruf(self, system: str, prompt: str, schema: type[BaseModel]) -> dict:
        from google.genai import errors, types

        for wartezeit in (2, 5, 10, None):  # 429 (Kontingent) mit Pause wiederholen
            try:
                return self._aufruf_einmal(system, prompt, schema, types)
            except errors.APIError as e:
                if getattr(e, "code", None) != 429 or wartezeit is None:
                    raise
                time.sleep(wartezeit)
        raise SprachmodellFehler("unerreichbar")

    def _aufruf_einmal(self, system: str, prompt: str, schema: type[BaseModel], types) -> dict:
        antwort = self._client_holen().models.generate_content(
            model=self.name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.3,
            ),
        )
        return json.loads(antwort.text or "{}")

    def json(self, system: str, prompt: str, schema: type[T]) -> T:
        def holen() -> dict:
            letzter_fehler: Exception | None = None
            for _ in range(2):
                try:
                    roh = self._aufruf(system, prompt, schema)
                    schema.model_validate(roh)
                    return roh
                except (ValidationError, json.JSONDecodeError) as e:
                    letzter_fehler = e
            raise SprachmodellFehler(f"Ungültige Modellantwort: {letzter_fehler}")

        try:
            roh = zwischengespeichert(
                "llm", holen, modell=self.name, system=system, prompt=prompt, schema=schema.__name__
            )
        except SprachmodellFehler:
            raise
        except Exception as e:  # Netz, Quota, Login
            raise SprachmodellFehler(f"Sprachmodell nicht erreichbar: {e}") from e
        return schema.model_validate(roh)


def analyse_modell() -> Sprachmodell:
    return GeminiModell(get_settings().llm_analyse_model)


def text_modell() -> Sprachmodell:
    s = get_settings()
    if s.llm_text_provider != "gemini":
        # Nur Gemini ist umgesetzt: einen fremden Modellnamen (z. B. claude-…) nie an Gemini schicken.
        return GeminiModell(s.llm_analyse_model)
    return GeminiModell(s.llm_text_model)
