# Sponsorenkompass

> **Der Sponsor um die Ecke: gefunden, begründet, angesprochen.**

Sponsorenkompass findet für Vereine passende Unternehmen im Umkreis, begründet jeden Vorschlag mit Quellen und bereitet eine persönliche Ansprache vor. Es setzt dort an, wo bestehende Tools aufhören: bei Sponsoren, die den Verein noch nicht kennen.

Entstanden am 7. November 2026 beim **Cursor × Sandbox Founders Hackathon** im CREATORS space, Stuttgart.

| | |
|---|---|
| 🎬 Pitch + Demo-Video | _Link folgt_ |
| 🖥️ Live-Demo | _Link folgt_ |
| 📊 Pitch-Deck | _Link folgt_ |

---

## Das Problem

Sponsorensuche ist Klinkenputzen. Ehrenamtliche ohne Vertriebserfahrung arbeiten mit Branchenbuch und Bauchgefühl, schreiben Massenbriefe ohne Bezug und hören selten etwas zurück. Die meisten lokalen Betriebe sind auf keiner Sponsoring-Plattform.

**Für wen:** Vorstand, Kassenwart oder Sponsoring-Verantwortliche kleiner und mittlerer Vereine, dazu Fördervereine und andere Gemeinnützige. Verbände und Sportkreise als Vertriebsweg.

## Die Lösung in vier Schritten

1. **Vereinsprofil anlegen**: Ort, Sportarten, Mitglieder, Zielgruppen, Reichweite, Sponsoring-Angebote.
2. **Kandidaten im Umkreis finden**: Betriebe aus offenen Kartendaten (OpenStreetMap), ergänzt durch Websuche.
3. **Passung recherchieren**: Jeder Kandidat bekommt eine Bewertung von 0 bis 100 mit drei Gründen und Quellenlinks, etwa lokales Engagement, bisheriges Sponsoring oder Nähe zur Zielgruppe.
4. **Ansprache vorbereiten**: Brief, Gesprächsleitfaden fürs Telefon und eine E-Mail für nach dem Erstkontakt. Status verfolgen und als CSV exportieren.

**Jede Aussage hat eine Quelle.** Das unterscheidet Sponsorenkompass von einer generierten Liste: Bewertungen entstehen nur aus tatsächlich gefundenen Texten. Wurde wenig gefunden, zeigt das Tool niedrige Sicherheit an, statt Gründe zu erfinden.

## Abgrenzung

| Angebot | Was es tut | Was fehlt |
|---|---|---|
| findasponsor, Motivation4Teams | Marktplatz: Vereine legen Profile an, Unternehmen suchen | Erreicht nur Unternehmen, die sich selbst anmelden |
| Clubvermarktung | Verwaltung von Sponsoren, Verträgen, Rechnungen | Keine aktive Suche nach neuen Sponsoren |
| Agenturen (etwa HeySponsor) | Persönliche Sponsorengewinnung | Für kleine Vereine zu teuer |
| Branchenbuch, Google Maps | Liste von Betrieben | Keine Begründung, keine Ansprache |
| **Sponsorenkompass** | **Sucht aktiv, begründet mit Quellen, bereitet Ansprache vor** | Verträge und Rechnungen übernehmen bestehende Tools |

---

## Funktionsumfang (MVP)

**Muss**
- [ ] Vereinsprofil als Formular
- [ ] Kandidaten im Umkreis aus OpenStreetMap: Name, Branche, Adresse, Website, Entfernung
- [ ] Vorfilter nach Branche und Entfernung (nur die besten 30 bis 50 werden recherchiert)
- [ ] Recherche pro Kandidat mit exa.ai: Website-Inhalte, lokales Engagement, bisheriges Sponsoring
- [ ] Bewertung 0 bis 100 mit drei Gründen und Quellenlinks
- [ ] Ansprache: Brief, Gesprächsleitfaden, E-Mail für nach dem Erstkontakt
- [ ] Liste und Karte mit Filtern, Status pro Kandidat (neu, kontaktiert, Termin, Zusage, Absage)
- [ ] Export als CSV

**Kann**
- [ ] „Ähnlich wie euer bester Sponsor“: bestehenden Sponsor eingeben, ähnliche Unternehmen finden
- [ ] Branchenkonflikte erkennen (z. B. zwei Autohäuser bei Exklusivität)
- [ ] Sponsoring-Mappe als PDF aus dem Vereinsprofil
- [ ] Erinnerung zum Nachfassen nach einer Woche
- [ ] Unternehmen per Website-Link manuell hinzufügen

**Bewusst nicht:** automatischer Massenversand, Login, Bezahlung, Verträge und Rechnungen.

---

## Architektur

```
Vereinsprofil ──► Geokodierung (Nominatim) ──► Betriebe im Umkreis (Overpass/OSM)
                                                        │
                                                        ▼
                                          Vorfilter: Branche + Entfernung
                                                        │  Top 30–50
                                                        ▼
                                          Recherche (exa.ai), mit Quellen
                                                        │
                                                        ▼
                                Bewertung + 3 Gründe + Ansprache (Sprachmodell)
                                                        │
                                                        ▼
                                     Liste · Karte · Detail · CSV-Export
```

Kostenlose Kartendaten liefern die Kandidaten, die kostenpflichtige Websuche läuft nur für die besten nach dem Vorfilter. Alle externen Abfragen werden zwischengespeichert, damit nichts doppelt bezahlt wird.

| Quelle | Wofür | Kosten |
|---|---|---|
| OpenStreetMap (Overpass API) | Betriebe im Umkreis | kostenlos |
| Nominatim | Vereinsort in Koordinaten | kostenlos (max. 1 Anfrage/s, eigener User-Agent) |
| exa.ai | Website-Inhalte, Hinweise auf Sponsoring und lokales Engagement | nach Verbrauch |
| Sprachmodell | Bewertung, Gründe, Ansprache | nach Verbrauch |

### Tech-Stack

- **Backend:** Python, FastAPI, SQLModel, SQLite (später PostgreSQL möglich)
- **Frontend:** Vite, React, TypeScript, Tailwind, react-leaflet
- **Tests:** pytest

Websuche und Sprachmodell liegen hinter je einer eigenen Schnittstelle (`app/providers`) und sind per Konfiguration austauschbar. Recherche und Bewertung laufen als Hintergrundaufgaben mit Fortschrittsanzeige.

### API

FastAPI erzeugt die API-Dokumentation automatisch unter `/docs`. So können andere Vereinsanwendungen später Kandidaten abrufen und Status zurückschreiben.

| Endpunkt | Zweck |
|---|---|
| `/vereine` | Vereinsprofil anlegen und lesen |
| `/kandidaten` | Suche im Umkreis |
| `/recherche` | Websuche pro Kandidat |
| `/bewertung` | Bewertung mit Gründen und Quellen |
| `/ansprache` | Brief, Gesprächsleitfaden, E-Mail |
| `/export` | CSV-Export |

---

## Lokal starten

### Voraussetzungen

- Python 3.11+
- Node.js 20+
- API-Keys für exa.ai und einen Sprachmodell-Anbieter

### Konfiguration

```bash
cp .env.example .env
```

In `.env` die Keys eintragen (`EXA_API_KEY` sowie der Key des Sprachmodell-Anbieters). Keys gehören nie ins Repository.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API läuft auf http://localhost:8000, Dokumentation unter http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Oberfläche läuft auf http://localhost:5173.

### Tests

```bash
cd backend
pytest
```

---

## Recht und Datenschutz

_Keine Rechtsberatung, vor einem Produktstart prüfen lassen._

- **Kein Massenversand aus dem Tool.** Der Verein entscheidet und versendet selbst.
- **Brief, Anruf oder persönlicher Kontakt zuerst.** Unaufgeforderte E-Mails können auch zwischen Unternehmen als Werbung gelten, deshalb kommt die E-Mail erst nach dem Erstgespräch.
- **Nur öffentliche Unternehmensdaten.** Ansprechpartner nur aus öffentlichen Angaben (etwa dem Impressum), sparsam gespeichert, mit Quelle.

---

## Team

**Timon**: Kassenwart eines Jugendfördervereins und Ausbilder für Vereinsmanager beim Südbadischen Fußballverband. Sponsoring ist in jedem Lehrgang Thema.

## Hackathon-Hinweis

Konzept, Recherche und Planung entstanden vor dem Hackathon, wie es die Regeln erlauben. Der gesamte Projektcode wurde am 7. November 2026 vor Ort geschrieben; die Commit-Historie zeigt den Verlauf.
