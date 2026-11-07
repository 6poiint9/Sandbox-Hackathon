# Sponsorenkompass

> **Der Sponsor um die Ecke: gefunden, begründet, angesprochen.**

Sponsorenkompass zeigt Vereinen in drei Minuten, wie viel Sponsoring-Potenzial in ihnen steckt: **welche Unternehmen in der Region passen** und **mit welchem Angebot** sie diese ansprechen. Jeder Vorschlag ist mit Quellen begründet, die Ansprache ist fertig vorbereitet, und bestehende Sponsoren werden gleich mitverwaltet.

Entstanden am 7. November 2026 beim **Cursor × Sandbox Founders Hackathon** im CREATORS space, Stuttgart.

| | |
|---|---|
| 🎬 Pitch + Demo-Video | _Link folgt_ |
| 🖥️ Live-Demo | _Link folgt_ |
| 📊 Pitch-Deck | [Google Slides](https://docs.google.com/presentation/d/1p4gav7rx0arVGWb5EWd1qgWBckvdj517CTxpvdoi-bI/edit) |

---

## Das Problem

Sponsorensuche ist Klinkenputzen. Ehrenamtliche ohne Vertriebserfahrung arbeiten mit Branchenbuch und Bauchgefühl, schreiben Massenbriefe ohne Bezug und hören selten etwas zurück. Viele Vereine wissen nicht einmal, was sie Sponsoren anbieten könnten und was das wert ist. Die meisten lokalen Betriebe sind auf keiner Sponsoring-Plattform.

**Für wen:** Vorstand, Kassenwart oder Sponsoring-Verantwortliche kleiner und mittlerer Vereine, dazu Fördervereine und andere Gemeinnützige. Verbände und Sportkreise als Vertriebsweg.

## Zwei Seiten, ein Abgleich

| Angebot: Was hat der Verein? | Nachfrage: Wer passt dazu? |
|---|---|
| Inventar aus dem [Sponsoring-Katalog](docs/sponsoring-katalog.md): Bande, Trikot, Social Media, Turniere, Azubi-Kooperation und mehr | Betriebe im Umkreis aus OpenStreetMap, recherchiert mit exa.ai |
| Was ist frei, was ist vergeben, was ist es wert? | Lokales Engagement, bisheriges Sponsoring, Nähe zur Zielgruppe |

Sponsorenkompass bringt beides zusammen: **Jeder Kandidat bekommt ein empfohlenes Paket**, etwa „Bäckerei Müller, 1,2 km, unterstützt schon das Stadtfest: Bande plus Stand beim Vereinsfest, ca. 600 € pro Saison“.

## Der Userflow

1. **Website eingeben (30 Sek.):** Website-URL und Ort. Die KI liest die Vereinsseite aus.
2. **Profil bestätigen (1–2 Min.):** Sportarten, Mannschaften, Spielklasse, Veranstaltungen und erkannte Sponsoren sind vorbefüllt. Der Vorstand korrigiert, beantwortet ein paar Fragen (Mitglieder, Zuschauer, Ziel) und hakt sein Angebots-Inventar ab. **Bestandssponsoren** lädt er als Liste hoch ([CSV-Vorlage](docs/vorlage-bestandssponsoren.csv)) oder ergänzt sie von Hand.
3. **Potenzialanalyse (der Wow-Moment):** Eine Zahl für das ungenutzte Potenzial pro Saison, der Angebotskatalog mit freien Paketen und Richtpreisen, die Top-Kandidaten auf der Karte und die Lücken („Ihr habt keine Bank, keine Bäckerei, kein Autohaus“).
4. **Kandidat öffnen:** drei Gründe mit Quellenlinks, empfohlenes Paket, fertiger Brief, Gesprächsleitfaden und E-Mail für nach dem Erstkontakt.
5. **Sponsoren verwalten:** Pipeline (neu → kontaktiert → Termin → Zusage/Absage) und bestehende Sponsoren mit Paket, Betrag und Laufzeit. Export als CSV.

**Jede Aussage hat eine Quelle.** Bewertungen entstehen nur aus tatsächlich gefundenen Texten. Wurde wenig gefunden, zeigt das Tool niedrige Sicherheit an, statt Gründe zu erfinden. Richtpreise sind als Richtwert gekennzeichnet.

## Abgrenzung

| Angebot | Was es tut | Was fehlt |
|---|---|---|
| findasponsor, Motivation4Teams | Marktplatz: Vereine legen Profile an, Unternehmen suchen | Erreicht nur Unternehmen, die sich selbst anmelden |
| Clubvermarktung | Verwaltung von Sponsoren, Verträgen, Rechnungen | Keine aktive Suche nach neuen Sponsoren |
| Agenturen (etwa HeySponsor) | Persönliche Sponsorengewinnung | Für kleine Vereine zu teuer |
| Branchenbuch, Google Maps | Liste von Betrieben | Keine Begründung, kein Angebot, keine Ansprache |
| **Sponsorenkompass** | **Potenzialanalyse, aktive Suche mit Quellen, passendes Paket, fertige Ansprache** | Verträge und Rechnungen übernehmen bestehende Tools |

---

## Funktionsumfang (Stand 7.11.2026)

**Fertig**
- [x] Landingpage mit Anmeldung für Warteliste und Pilotvereine
- [x] Onboarding **nur mit der Website**: Profil, Mannschaften, Spielklasse, Veranstaltungen
- [x] **Sportstätte** statt Impressumsadresse als Mittelpunkt der Suche (oft stehen dort Privatadressen)
- [x] Bestandssponsoren aus Text **und aus Logos** (Gemini liest die Logos der Sponsorenseite), CSV-Import
- [x] Angebots-Inventar aus dem Sponsoring-Katalog
- [x] Betriebe im Umkreis (Google Places, OpenStreetMap als Ausweichweg), Vorfilter, Lücken nach Branchen
- [x] Recherche mit exa.ai, Bewertung 0–100 mit drei Gründen und Quellenlinks, empfohlenes Paket mit Richtpreis
- [x] Potenzialanalyse: ungenutztes Potenzial pro Saison, freie Pakete, Annahmen offengelegt
- [x] Analyse im Hintergrund – kein Warten, optional E-Mail, wenn alles fertig ist
- [x] Ansprache: Brief, Telefonleitfaden, E-Mail für nach dem Erstkontakt
- [x] **Sponsoren-CRM**: Bestand bearbeiten, Kontakt, Status, Betrag, Laufzeit, Verlauf, Wiedervorlagen, auslaufende Verträge
- [x] **Assets**: Banden, Trikots, Social Media … mit Anzahl, Vergaben an Sponsoren, Preis, Laufzeit
- [x] Kandidat nach Zusage als Sponsor übernehmen
- [x] **Konten** nach aktuellem Sicherheitsstandard (siehe Sicherheit); Analyse nur nach Anmeldung
- [x] CSV-Export

**Als Nächstes**
- [ ] „Ähnlich wie euer bester Sponsor“
- [ ] Branchenkonflikte erkennen (z. B. zwei Autohäuser bei Exklusivität)
- [ ] Sponsoring-Mappe als PDF
- [ ] E-Mail-Bestätigung, Passwort zurücksetzen, Zwei-Faktor/Passkeys

**Bewusst nicht:** automatischer Massenversand, Bezahlung, Vertragsdokumente und Rechnungen.

---

## Daten, die mit jedem Verein besser werden

Die Richtpreise starten heute mit belegten Marktwerten (z. B. Trikotbrust 1.500–5.000 €, Bande 300–1.500 € pro Saison laut findasponsor) und begründeten Schätzungen, skaliert nach Spielklasse und Zuschauern. Jeder Verein trägt beim Onboarding ein, was er anbietet, was er dafür bekommt und welche Anfragen zu Zusagen führen. Mit genug Vereinen ersetzen echte Werte die Schätzungen: bessere Preisempfehlungen und treffsicherere Vorschläge für alle (anonymisiert, nur mit Zustimmung).

---

## Architektur

```
Website-URL ──► Profil-Extraktion (exa + Sprachmodell) ──► Vereinsprofil + Inventar + Bestandssponsoren
                                                                     │
Ort ──► Geokodierung (Nominatim) ──► Betriebe im Umkreis (Overpass/OSM)
                                                     │
                                                     ▼
                                   Vorfilter: Branche, Entfernung, Lücken
                                                     │  Top 15–30
                                                     ▼
                                   Recherche (exa.ai), mit Quellen
                                                     │
                                                     ▼
                     Bewertung + 3 Gründe + Paket-Empfehlung + Ansprache (Sprachmodell)
                                                     │
                                                     ▼
                       Potenzialanalyse · Karte · Detail · Pipeline · CSV-Export
```

Kostenlose Kartendaten liefern die Kandidaten, die kostenpflichtige Websuche läuft nur für die besten nach dem Vorfilter. Alle externen Abfragen werden zwischengespeichert.

| Quelle | Wofür | Kosten |
|---|---|---|
| OpenStreetMap (Overpass API) | Betriebe im Umkreis | kostenlos |
| Nominatim | Vereinsort in Koordinaten | kostenlos (max. 1 Anfrage/s, eigener User-Agent) |
| exa.ai | Vereinswebsite, Website-Inhalte der Kandidaten, Hinweise auf Sponsoring | nach Verbrauch |
| Sprachmodell | Profil-Extraktion, Bewertung, Paket, Ansprache | nach Verbrauch |

### Tech-Stack

- **Backend:** Python, FastAPI, SQLModel, SQLite
- **Frontend:** Vite, React, TypeScript, Tailwind, react-leaflet
- **Tests:** pytest

Websuche und Sprachmodell liegen hinter je einer eigenen Schnittstelle und sind per Konfiguration austauschbar. Recherche und Bewertung laufen als Hintergrundaufgaben mit Fortschrittsanzeige.

### API

Die API-Dokumentation erzeugt FastAPI automatisch unter `/docs`.

| Endpunkt | Zweck |
|---|---|
| `POST /onboarding/analyse` | Website auslesen, Profilvorschlag zurückgeben |
| `/vereine` | Vereinsprofil anlegen, lesen, ändern |
| `/vereine/{id}/inventar` | Angebots-Inventar (frei / vergeben, Preis) |
| `/vereine/{id}/sponsoren` | Bestandssponsoren, inkl. CSV-Import |
| `/vereine/{id}/kandidaten` | Suche im Umkreis, Recherche und Bewertung starten |
| `/vereine/{id}/potenzial` | Potenzialanalyse |
| `/kandidaten/{id}/ansprache` | Brief, Gesprächsleitfaden, E-Mail |
| `/vereine/{id}/export` | CSV-Export |

---

## Lokal starten

### Voraussetzungen

- Python 3.11+
- Node.js 20+
- API-Keys für exa.ai und einen Sprachmodell-Anbieter

### Konfiguration

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Keys in `backend/.env` eintragen (eine `.env` im Hauptordner wird ebenfalls gelesen). Keys gehören nie ins Repository. Mit `DEMO_MODE=1` läuft die App ohne externe Aufrufe aus zwischengespeicherten Demo-Daten.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API auf http://localhost:8000, Dokumentation unter http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Oberfläche auf http://localhost:5173.

### Tests

```bash
cd backend
pytest
```

---

## Sicherheit

Analysen gibt es nur mit Konto; alle Vereinsdaten sind ausschließlich für das eigene Konto sichtbar. Umgesetzt nach OWASP ASVS und NIST SP 800-63B:

- **Passwörter:** Argon2id (64 MiB, 3 Durchläufe), mindestens 12 Zeichen, keine häufigen oder aus Datenlecks bekannten Passwörter (Have I Been Pwned, k-Anonymität – nur 5 Zeichen eines Hashes verlassen den Server)
- **Sitzung:** zufälliges 256-Bit-Token nur im `__Host-`-Cookie mit `HttpOnly`, `Secure`, `SameSite=Strict`; in der Datenbank nur sein SHA-256. 7 Tage absolute Laufzeit, Abmeldung nach 24 h Inaktivität, neue Sitzung bei jeder Anmeldung, „auf allen Geräten abmelden“, Passwortwechsel beendet andere Sitzungen
- **Angriffsschutz:** Begrenzung von Anmeldeversuchen (E-Mail und IP), gleiche Antwort und Laufzeit bei unbekannter E-Mail, CSRF-Header- und Origin-Prüfung, Sicherheits-Header (HSTS, CSP, X-Frame-Options, nosniff), Kostenbremse für Analysen je Konto
- **Mandantentrennung:** Jedes Konto ist ein Mandant. Alle Vereinsdaten (Verein, Sponsoren, Kandidaten, Ansprachen, Assets, Vergaben, Aktivitäten) hängen über den Verein am Konto; jede ID im Pfad und jede ID im Anfragetext wird gegen den Mandanten geprüft, Fremdes ist 404 (verrät nicht einmal die Existenz). Zwei automatische Tests sichern das ab: Jeder Endpunkt muss geschützt oder ausdrücklich öffentlich sein, und ein zweiter Mandant ruft jeden Endpunkt mit jeder Methode und fremden IDs auf, ohne je Erfolg zu haben ([tests/test_mandanten.py](backend/tests/test_mandanten.py)). Gemeinsam genutzt werden nur öffentliche Daten (Betriebe aus Google/OSM, Sponsoring-Katalog, Website-Abrufe).
- **Betrieb:** Frontend und API auf demselben Ursprung (lokal über den Vite-Proxy `/api`), in Produktion nur über HTTPS

Noch offen: E-Mail-Bestätigung und Passwort-Zurücksetzen (brauchen SMTP), Zwei-Faktor-Anmeldung bzw. Passkeys, Begrenzer für mehrere Server (z. B. Redis).

## Recht und Datenschutz

_Keine Rechtsberatung, vor einem Produktstart prüfen lassen._

- **Kein Massenversand aus dem Tool.** Der Verein entscheidet und versendet selbst.
- **Brief, Anruf oder persönlicher Kontakt zuerst.** Unaufgeforderte E-Mails können auch zwischen Unternehmen als Werbung gelten, deshalb kommt die E-Mail erst nach dem Erstgespräch.
- **Nur öffentliche Unternehmensdaten.** Ansprechpartner nur aus öffentlichen Angaben (etwa dem Impressum), sparsam gespeichert, mit Quelle.
- **Bestandssponsoren** sind Daten des Vereins und werden nur für ihn genutzt. Auswertungen über Vereine hinweg nur anonymisiert und mit Zustimmung.

---

## Projektunterlagen

- [Fahrplan für den Bau](docs/fahrplan.md)
- [Sponsoring-Katalog](docs/sponsoring-katalog.md)
- [CSV-Vorlage Bestandssponsoren](docs/vorlage-bestandssponsoren.csv)
- [CLAUDE.md](CLAUDE.md): Arbeitsregeln für die KI-Assistenz beim Bauen

## Team

**Timon**: Kassenwart eines Jugendfördervereins und Ausbilder für Vereinsmanager beim Südbadischen Fußballverband. Sponsoring ist in jedem Lehrgang Thema.

## Hackathon-Hinweis

Konzept, Recherche und Planung entstanden vor dem Hackathon, wie es die Regeln erlauben. Der gesamte Projektcode wurde am 7. November 2026 vor Ort geschrieben; die Commit-Historie zeigt den Verlauf.
