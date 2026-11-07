# Fahrplan: Sponsorenkompass an einem Tag

**Ziel:** Um 15:30 läuft der komplette Demo-Durchlauf mit einem echten Verein, live und im `DEMO_MODE`. Danach nur noch Deploy, Video, Deck.

**Leitlinie:** Erst ein dünner Durchstich durch alle Schritte, dann besser machen. Jede Phase endet mit einem Commit und einem Kurztest im Browser oder unter `/docs`.

## Vor dem Start (bis 11:00, parallel)

- [ ] Accounts: Credits für Exa, Cursor und Google AI einlösen (Google nur bis 13:00!), Sprachmodell-Key bereit
- [ ] Team im Portal anlegen und sperren (Frist 11:30)
- [ ] Demo-Verein festlegen: Website-URL, Ort, Radius (z. B. 15 km), Erlaubnis des Vorstands
- [ ] Bestandssponsoren des Demo-Vereins in `docs/vorlage-bestandssponsoren.csv`-Form notieren
- [ ] Mittags 2–3 Vorstände anrufen (Fragen in `docs/sponsoring-katalog.md` → „Erhebung“)

## Phasen

| Zeit | Phase | Ergebnis | Notbremse, wenn es klemmt |
|---|---|---|---|
| 11:00–11:30 | 1 Setup | Backend + Frontend starten, Katalog als JSON, Healthcheck | Frontend erst als eine Seite |
| 11:30–12:15 | 2 Onboarding | Website-URL → Profilvorschlag, Profil speichern, Inventar abhaken, CSV-Import | Profil nur als Formular, ohne Extraktion |
| 12:15–13:00 | 3 Kandidaten | Geokodierung, OSM-Betriebe, Vorfilter, Lücken | feste Branchenliste statt Lückenlogik |
| 13:00–13:45 | 4 Recherche + Bewertung | exa-Recherche Top 15, Score, 3 Gründe, Paket-Empfehlung | Top 5 statt Top 15 |
| 13:45–14:15 | 5 Potenzial + Ansprache | Potenzialzahl, Brief, Leitfaden, E-Mail | nur Brief |
| 14:15–15:15 | 6 Oberfläche | Potenzialanalyse-Screen, Liste + Karte, Detail, Pipeline | Karte weglassen, nur Liste |
| 15:15–15:30 | 7 Demo-Daten einfrieren | Demo-Verein komplett durchlaufen, `cache/demo/` füllen, `DEMO_MODE` testen | — |
| **15:30** | **Feature-Freeze** | | |
| 15:30–16:00 | 8 Deploy | Backend (Render/Railway), Frontend statisch, Links prüfen | lokal aufnehmen, Link „Demo auf Anfrage“ weglassen |
| 16:00–16:40 | 9 Video + Deck | 3-Min-Video (Pitch + Demo), max. 5 Folien | — |
| 16:40–17:00 | 10 Einreichen | README-Links eintragen, Repo öffentlich, im Portal einreichen | — |

Die Kann-Liste (ähnliche Unternehmen, Branchenkonflikte, PDF-Mappe) nur, wenn um 14:15 alles bis Phase 5 läuft.

**Deploy-Probe in der Mittagspause (12:30):** Das leere Gerüst mit `/health` einmal auf Render/Railway und das Frontend statisch deployen. Wer erst um 15:30 zum ersten Mal deployt, findet die Probleme zu spät.

## Gegen die typischen Vibe-Coding-Fehler

| Fehler | Unsere Gegenmaßnahme |
|---|---|
| Riesenprompt „bau mir die App“ | 7 Phasen, jede ein Durchstich |
| Fehler stapeln sich unbemerkt | nach jeder Phase starten und im Browser oder unter `/docs` klicken |
| KI repariert denselben Fehler fünfmal | nach 2 Versuchen auf den letzten Commit zurück und neu formulieren |
| Kein sauberer Rückweg | nach jedem funktionierenden Schritt sofort committen und pushen |
| Erfundene API-Parameter oder Modellnamen | Doku oder echter Testaufruf, siehe CLAUDE.md |
| API-Key im öffentlichen Repo | Keys nur in `.env`, `.gitignore` ab Phase 1, Diff vor jedem Push prüfen |
| KI vergisst die Regeln, Kontext läuft voll | `/clear` pro Phase, Regeln stehen in CLAUDE.md |
| Zwei Tools ändern dieselben Dateien | Claude Code baut; Cursor nur für kleine UI-Feinheiten, nie gleichzeitig an derselben Datei |
| Code, den niemand erklären kann | nach jeder Phase 3 Sätze erklären lassen: was, wo, warum (Jury-Fragen) |
| Live-Demo hängt an langsamer API | Cache, `DEMO_MODE`, Demo-Daten ab 15:15 eingefroren |
| Polieren statt fertig werden | Feature-Freeze 15:30, Notbremse pro Phase |
| Erster Deploy kurz vor Schluss | Deploy-Probe um 12:30 |

## Prompts

Jeweils in einer neuen Unterhaltung oder nach `/clear` starten. Die Regeln stehen in `CLAUDE.md`, deshalb sind die Prompts kurz. Bei größeren Phasen erst einen Plan zeigen lassen, dann bauen.

### Phase 1: Setup

```
Lies CLAUDE.md und README.md. Lege die Projektstruktur aus CLAUDE.md an:
FastAPI-Backend mit SQLModel/SQLite, config.py mit Umgebungsvariablen,
.env.example (EXA_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY,
LLM_ANALYSE_PROVIDER, LLM_ANALYSE_MODEL, LLM_TEXT_PROVIDER, LLM_TEXT_MODEL,
DEMO_MODE, FRONTEND_URL, VITE_API_URL),
requirements.txt, GET /health, pytest-Grundgerüst. Wandle docs/sponsoring-katalog.md
in backend/app/data/katalog.json um (id, kategorie, name, gegenleistung,
zielbranchen, preis_min, preis_max, einheit, quelle oder "schaetzung").
Frontend mit Vite, React, TypeScript, Tailwind, react-leaflet, das /health anzeigt.
.gitignore für .env, .venv, node_modules, *.db, cache/ (außer cache/demo/).
Noch keine Fachlogik.
```

### Phase 2: Onboarding

```
Baue das Onboarding laut README (Userflow Schritte 1–2) und Datenmodell aus CLAUDE.md.
1) Provider-Schnittstellen websuche (exa) und llm, austauschbar, mit Cache und DEMO_MODE.
2) POST /onboarding/analyse {website, ort}: Vereinswebsite und Unterseiten
   (Mannschaften, Sponsoren, Termine) über exa holen, per Sprachmodell als JSON
   (Pydantic) extrahieren: Profilfelder, erkannte Sponsoren, vorhandene Inventarposten
   aus katalog.json. Unsichere Felder als leer zurückgeben, nichts erfinden.
3) CRUD für Verein, InventarPosten und Sponsor.
4) POST /vereine/{id}/sponsoren/import für CSV nach docs/vorlage-bestandssponsoren.csv;
   Semikolon und Komma akzeptieren, fehlerhafte Zeilen melden statt abbrechen.
Tests für CSV-Import und das Extraktions-Schema. Zeig mir erst den Plan.
```

### Phase 3: Kandidaten

```
Baue services/geo (Nominatim, Regeln aus CLAUDE.md), services/osm (Overpass,
Radius um den Verein) und services/vorfilter. Vorfilter-Score aus Entfernung und
Branchenpassung zu den freien Inventarposten (zielbranchen im Katalog), Bonus für
Branchen ohne Bestandssponsor (Lücken). Bestandssponsoren aus der Kandidatenliste
ausschließen. POST /vereine/{id}/kandidaten speichert die besten N mit Status "neu".
Tests für den Vorfilter.
```

### Phase 4: Recherche und Bewertung

```
Baue Recherche und Bewertung als Hintergrundaufgabe mit Fortschritt
(GET /vereine/{id}/kandidaten/status). Pro Kandidat: Website und Hinweise auf
Sponsoring, Vereinsförderung, lokales Engagement über exa holen, Quellen speichern.
Dann per Sprachmodell (JSON, Pydantic): score 0–100, sicherheit, genau 3 Gründe
mit quelle_url aus den gespeicherten Quellen, paket_empfehlung aus den FREIEN
Inventarposten (nur katalog_ids und Begründung; Preis rechnet der Code).
Fehler pro Kandidat abfangen. Erst mit 3 Kandidaten testen, dann Top 15.
```

### Phase 5: Potenzial und Ansprache

```
Baue services/potenzial nach der Potenzial-Logik in CLAUDE.md:
GET /vereine/{id}/potenzial liefert Spanne in Euro, freie Pakete mit Richtpreis,
Lücken (Branchen) und Top-10-Kandidaten. Tests dafür.
Dann POST /kandidaten/{id}/ansprache: Brief, Telefonleitfaden und E-Mail für nach
dem Erstkontakt, jeweils mit Bezug auf die Gründe und das empfohlene Paket.
GET /vereine/{id}/export als CSV.
```

### Phase 6: Oberfläche

```
Baue das Frontend mit vier Ansichten, ruhige Farben, eine Akzentfarbe für Scores,
mobil nutzbar:
1) Onboarding: Website + Ort → "Potenzial analysieren" → vorbefülltes Profil
   korrigieren, Fragen, Inventar abhaken, CSV hochladen.
2) Potenzialanalyse (der Wow-Screen): große Potenzialzahl als Spanne mit Hinweis
   "Richtwert", freie Pakete, Lücken, Karte mit Top-Kandidaten. Kandidaten
   erscheinen nacheinander, während die Recherche läuft.
3) Kandidat-Detail: Steckbrief, 3 Gründe mit klickbaren Quellen, empfohlenes Paket,
   Reiter Brief/Leitfaden/E-Mail mit "Kopieren", Status-Knöpfe.
4) Sponsoren: Pipeline nach Status und Liste der Bestandssponsoren, CSV-Export.
```

### Phase 7: Demo einfrieren

```
Lass den Demo-Verein einmal komplett durchlaufen und speichere alle externen
Antworten in backend/cache/demo/. Prüfe, dass mit DEMO_MODE=1 der ganze Flow
ohne Netz funktioniert. Ergänze in der README die Befehle für den Demo-Start.
```

## Demo-Ablauf (für Video und Bühne)

1. Website des Demo-Vereins eingeben → Profil füllt sich von selbst.
2. Zwei Fragen beantworten, Bestandssponsoren-CSV hochladen.
3. Potenzialanalyse: „ca. X–Y € ungenutzt“, Lücken, Karte füllt sich.
4. Bester Kandidat: drei Gründe mit Quellen, empfohlenes Paket.
5. Reiter „Brief“: persönliche Anfrage mit echtem Bezug. Status auf „kontaktiert“.

Fallback: Wenn live etwas hängt, `DEMO_MODE=1` und das offen sagen.
