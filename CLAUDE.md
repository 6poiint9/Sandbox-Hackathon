# CLAUDE.md – Sponsorenkompass

Hackathon-Projekt, Abgabe **heute, 7.11.2026, 17:00 Uhr**. Feature-Freeze 15:30. Stabilität schlägt Umfang.
Produktbeschreibung und Userflow: `README.md`. Bau-Reihenfolge: `docs/fahrplan.md`.

## Arbeitsweise

- **Kleine, senkrechte Schritte.** Ein Schritt = eine Funktion, die durchgehend läuft (API + minimale UI oder Test). Nach jedem Schritt: starten, prüfen, committen.
- **Sofort committen und pushen**, ohne auf Freigabe zu warten. Nach jedem funktionierenden Schritt `git add`, Diff auf Secrets prüfen, `git commit`, `git push`.
- **Nur ändern, worum gebeten wurde.** Keine ungefragten Refactorings, keine neuen Bibliotheken ohne Rückfrage.
- **Erst lesen, dann schreiben.** Bestehende Dateien ansehen, bevor neue mit ähnlichem Zweck entstehen.
- **Externe APIs nicht aus dem Gedächtnis.** Für exa.ai, Overpass, Nominatim und das Sprachmodell die aktuelle Doku prüfen oder einen echten Testaufruf machen.
- **Fehler pro Kandidat abfangen.** Ein kaputter Kandidat darf nie die ganze Analyse stoppen.
- Kommunikation mit dem Nutzer auf Deutsch. Code, Kommentare und Commit-Messages auf Deutsch oder Englisch, aber einheitlich pro Datei.

## Wo KI eingesetzt wird und wo nicht

| Aufgabe | Wer | Warum |
|---|---|---|
| Vereinswebsite und Kandidaten-Websites lesen, Engagement finden | exa.ai | liefert Text mit URL, also Quellen |
| Profil aus Website-Text extrahieren | Sprachmodell „Analyse“ | unstrukturierter Text → JSON |
| Score, 3 Gründe, Paketwahl | Sprachmodell „Analyse“ | Abwägen, aber nur aus gespeicherten Quellen |
| Brief, Leitfaden, E-Mail | Sprachmodell „Text“ | das liest die Jury, Ton zählt |
| Geokodierung, Betriebe im Umkreis | Nominatim, Overpass | Fakten, keine KI |
| Entfernung, Vorfilter, Lücken, **Preise, Potenzialzahl**, CSV-Import, Export | normaler Python-Code | muss nachvollziehbar und testbar sein |

Faustregel: **Rechnen, zählen, filtern macht der Code. Lesen und formulieren macht die KI.**

## Verbotene Fehler (gelten bei jeder Änderung)

1. **Keine Secrets im Repo.** Vor jedem Commit `git diff --cached` auf Keys prüfen. Das Repo wird öffentlich.
2. **Keine erfundenen APIs, Parameter oder Modellnamen.** Unsicher → Doku lesen oder Testaufruf, nicht raten.
3. **Keine Fehlerschleifen.** Wenn derselbe Fehler nach 2 Versuchen bleibt: anhalten, Ursache erklären, dem Nutzer Rückbau auf den letzten Commit vorschlagen.
4. **Keine stillen Platzhalter.** Kein Fake-Erfolg, keine hartkodierten Beispieldaten im echten Ablauf. Demo-Daten nur über `DEMO_MODE`.
5. **Keine großen Umbauten.** Ein Auftrag ändert nur die Dateien, die er braucht. Keine Umbenennung der Begriffe aus dem Datenmodell.
6. **Keine neuen Abhängigkeiten ohne Rückfrage.** Versionen in requirements.txt / package.json festschreiben.
7. **Fehler nicht verschlucken.** Kein leeres `except`. Fehler loggen und pro Kandidat als Status sichtbar machen.
8. **Vertrag Backend ↔ Frontend einhalten.** Pydantic-Antwortmodelle sind die Wahrheit; das Frontend nutzt dieselben Feldnamen. API-Basis-URL und CORS über die Umgebung.
9. **Nach jeder Änderung selbst prüfen:** Backend startet, betroffener Endpunkt antwortet, Tests laufen. Erst dann „fertig“ melden und sagen, was nicht geprüft wurde.

## Struktur

```
backend/
  app/
    main.py           FastAPI-App, CORS, Router
    config.py         Einstellungen aus Umgebungsvariablen
    db.py             SQLModel, SQLite (sponsorenkompass.db)
    models.py         Datenmodell
    routers/          ein Router pro Bereich (onboarding, vereine, sponsoren, kandidaten, potenzial, ansprache, export)
    services/         Fachlogik (geo, osm, vorfilter, recherche, bewertung, potenzial, ansprache, csv_import)
    providers/        austauschbare Anbieter: websuche (exa), llm (Sprachmodell)
    data/katalog.json Sponsoring-Katalog (aus docs/sponsoring-katalog.md)
  cache/              JSON-Cache externer Aufrufe (nicht im Repo, außer demo/)
  cache/demo/         eingefrorene Ergebnisse des Demo-Vereins (im Repo)
  tests/
frontend/             Vite + React + TypeScript + Tailwind + react-leaflet
docs/
```

## Datenmodell (Begriffe fest, nicht umbenennen)

- **Verein**: name, website, ort, lat, lon, sportarten, mannschaften, spielklasse, mitglieder, zuschauer_schnitt, zielgruppen, reichweite (social, website), veranstaltungen, radius_km, ziel_eur
- **InventarPosten**: verein_id, katalog_id, verfuegbar (bool), vergeben_an (sponsor_id, optional), preis_eur (optional, sonst Richtwert)
- **Sponsor** (bestehend): verein_id, firma, website, gegenleistung (katalog_id), betrag_eur, laufzeit_bis, notiz
- **Unternehmen**: osm_id, name, branche, adresse, lat, lon, website
- **Kandidat**: verein_id, unternehmen_id, entfernung_km, vorfilter_score, score (0–100), sicherheit (niedrig/mittel/hoch), gruende (genau 3, je mit quelle_url), paket_empfehlung (katalog_ids + preis_eur + begruendung), status (neu, kontaktiert, termin, zusage, absage)
- **Ansprache**: kandidat_id, brief, leitfaden, email
- **Quelle**: url, auszug, abgerufen_am

## Regeln für KI-Ausgaben

- Jede Sprachmodell-Antwort als **JSON nach festem Schema**, validiert mit Pydantic. Bei ungültiger Antwort einmal neu versuchen, dann sauber als Fehler markieren.
- **Nichts erfinden.** Gründe nur aus gespeicherten Textauszügen, jeder Grund mit `quelle_url`. Wenig gefunden → `sicherheit: niedrig`.
- **Preise** kommen aus `katalog.json` × Faktor (siehe unten), nie frei vom Sprachmodell. Das Sprachmodell wählt nur die Pakete aus und begründet sie.
- **Ansprache:** Brief und Leitfaden zuerst, E-Mail nur „für nach dem Erstkontakt“. Kein Versand aus dem Tool.
- Prompts liegen als Konstanten in `services/`, nicht verstreut im Code.

## Potenzial-Logik (bewusst einfach, transparent)

- Faktor Spielklasse: Kreisklasse 0,6 · Kreisliga 0,8 · Bezirksliga 1,0 · Landesliga 1,3 · höher 1,6 (Jugend-only 0,7)
- Faktor Zuschauer: < 50 → 0,8 · 50–200 → 1,0 · > 200 → 1,2
- Potenzial = Summe über freie Inventarposten (Richtwert-Mitte × Faktoren), als Spanne (untere/obere Grenze) ausgeben.
- Lücken = Zielbranchen aus dem Katalog, in denen weder Bestandssponsor noch Zusage existiert.
- Werte gelten als Richtwert und werden in der UI so beschriftet.

## Externe Dienste

- **Nominatim:** eigener User-Agent `Sponsorenkompass/0.1 (Hackathon)`, max. 1 Anfrage/s, Ergebnis cachen.
- **Overpass:** shop, craft, office, amenity (Gastronomie, Banken), healthcare im Radius; Ergebnis cachen; Duplikate zusammenführen.
- **exa.ai:** Key aus `EXA_API_KEY`. Nur für Vereinswebsite und die Top-Kandidaten nach Vorfilter. Jede Antwort cachen.
- **Sprachmodell:** zwei Rollen, je Anbieter und Modell aus der Umgebung:
  - `LLM_ANALYSE_PROVIDER` / `LLM_ANALYSE_MODEL`: Profil-Extraktion, Bewertung, Paketwahl (viele Aufrufe, JSON). Standard: Gemini (Flash-Klasse) über die Google-AI-Credits.
  - `LLM_TEXT_PROVIDER` / `LLM_TEXT_MODEL`: Brief, Leitfaden, E-Mail (wenige Aufrufe, Qualität zählt). Standard: Claude, `claude-sonnet-5-5`. Ohne Anthropic-Key auch hier Gemini.
  - Keys: `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`. Modellnamen nie raten, sondern in der Anbieter-Doku prüfen.
- **`DEMO_MODE=1`:** keine externen Aufrufe, alles aus `cache/demo/`. Muss immer funktionieren.

## Sicherheit

- **Mandantentrennung ist Pflicht.** Jeder neue Router wird in `main.py` mit `dependencies=[Depends(zugriff)]` eingebunden. IDs im Pfad heißen `verein_id`, `kandidat_id`, `sponsor_id`, `asset_id`, `vergabe_id` oder `aktivitaet_id` (dann prüft `zugriff` automatisch). IDs im Anfragetext immer mit `verein_von` gegen den Verein prüfen. Fremdes ist 404. `tests/test_mandanten.py` muss grün bleiben – öffentliche Endpunkte nur nach Rückfrage in `OEFFENTLICH` eintragen.
- Anmeldung nur über das HttpOnly-Cookie; kein Token in JavaScript, localStorage oder URLs. Zustandsändernde Anfragen brauchen den Header `X-Sponsorenkompass: 1`.

- Keys nur in `.env`, nie im Code, nie im Repo. `.env.example` ohne echte Werte pflegen.
- Personenbezogene Daten: nur öffentliche Kontakte (Impressum), mit Quelle.

## Befehle

```bash
# Backend
cd backend && uvicorn app.main:app --reload
cd backend && pytest
# Frontend
cd frontend && npm run dev
cd frontend && npm run build
```

## Tests (nur das Wichtige)

Pflicht: Potenzialberechnung, CSV-Import der Bestandssponsoren, Vorfilter, Pydantic-Schemas der KI-Antworten. Externe Dienste in Tests immer mocken.
