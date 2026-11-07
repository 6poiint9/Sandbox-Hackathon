import type { ReactNode } from 'react'
import { ANBIETER, AUFSICHT, HOSTING, STAND, hatPlatzhalter } from '../rechtliches'

function Seite({ titel, children }: { titel: string; children: ReactNode }) {
  return (
    <article className="mx-auto max-w-3xl space-y-5 text-sm leading-relaxed text-slate-700">
      <h1 className="text-2xl font-semibold text-slate-900">{titel}</h1>
      {hatPlatzhalter() && (
        <p className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900">
          Entwurf: Angaben in [eckigen Klammern] fehlen noch (Datei <code>frontend/src/rechtliches.ts</code>). Vor dem
          Livegang ausfüllen und rechtlich prüfen lassen.
        </p>
      )}
      {children}
    </article>
  )
}

function Abschnitt({ titel, children }: { titel: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="pt-2 text-base font-semibold text-slate-900">{titel}</h2>
      {children}
    </section>
  )
}

function Anschrift() {
  return (
    <p>
      {ANBIETER.name}
      <br />
      {ANBIETER.strasse}
      <br />
      {ANBIETER.plzOrt}
      <br />
      {ANBIETER.land}
    </p>
  )
}

export function Impressum() {
  return (
    <Seite titel="Impressum">
      <Abschnitt titel="Angaben gemäß § 5 DDG">
        <Anschrift />
        {ANBIETER.zusatz.map((z) => <p key={z}>{z}</p>)}
      </Abschnitt>
      <Abschnitt titel="Kontakt">
        <p>
          E-Mail: {ANBIETER.email}
          {ANBIETER.telefon && <><br />Telefon: {ANBIETER.telefon}</>}
        </p>
      </Abschnitt>
      <Abschnitt titel="Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV">
        <p>{ANBIETER.verantwortlichInhalt}</p>
      </Abschnitt>
      <Abschnitt titel="Hinweis zum Projektstand">
        <p>
          Sponsorenkompass ist ein Prototyp, entstanden beim Cursor × Sandbox Founders Hackathon in Stuttgart (November 2026).
          Bewertungen, Richtpreise und Anschreiben werden teilweise automatisiert erstellt und sind Vorschläge – sie ersetzen keine
          eigene Prüfung durch den Verein.
        </p>
      </Abschnitt>
      <Abschnitt titel="Verbraucherstreitbeilegung">
        <p>Wir sind nicht bereit oder verpflichtet, an Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.</p>
      </Abschnitt>
      <Abschnitt titel="Haftung für Inhalte und Links">
        <p>
          Wir erstellen die Inhalte mit Sorgfalt, übernehmen aber keine Gewähr für Richtigkeit, Vollständigkeit und Aktualität.
          Vorschläge zu Unternehmen beruhen auf öffentlich zugänglichen Quellen, die wir verlinken. Für Inhalte externer Seiten sind
          deren Betreiber verantwortlich. Bei Bekanntwerden von Rechtsverletzungen entfernen wir betroffene Inhalte umgehend.
        </p>
      </Abschnitt>
    </Seite>
  )
}

export function Datenschutz() {
  const verantwortlich = `${ANBIETER.name}, ${ANBIETER.strasse}, ${ANBIETER.plzOrt}, E-Mail: ${ANBIETER.email}`
  return (
    <Seite titel="Datenschutzerklärung">
      <p className="text-xs text-slate-500">Stand: {STAND}</p>

      <Abschnitt titel="1. Verantwortlicher">
        <p>{verantwortlich}</p>
        <p>
          Für Daten, die Vereine in Sponsorenkompass über ihre eigenen Sponsoren und Kontakte pflegen, ist der jeweilige Verein
          Verantwortlicher; wir verarbeiten diese Daten in seinem Auftrag (Art. 28 DSGVO).
        </p>
      </Abschnitt>

      <Abschnitt titel="2. Überblick">
        <p>
          Wir verarbeiten nur, was für den Dienst nötig ist. Wir setzen keine Werbe- oder Analyse-Tracker ein und setzen nur ein
          technisch notwendiges Cookie für die Anmeldung. Daten verschiedener Konten sind strikt voneinander getrennt.
        </p>
      </Abschnitt>

      <Abschnitt titel="3. Aufruf der Website und Hosting">
        <p>
          Beim Aufruf verarbeitet der Server technisch notwendige Daten (IP-Adresse, Zeitpunkt, abgerufene Seite, Browser­angaben),
          um die Seite auszuliefern und vor Missbrauch zu schützen – etwa durch Begrenzung von Anmeldeversuchen. Rechtsgrundlage ist
          unser berechtigtes Interesse an einem sicheren Betrieb (Art. 6 Abs. 1 lit. f DSGVO). Hosting: {HOSTING}.
        </p>
      </Abschnitt>

      <Abschnitt titel="4. Konto und Anmeldung">
        <p>
          Für ein Konto speichern wir E-Mail-Adresse, optional einen Namen und Ihr Passwort ausschließlich als Argon2id-Hash – im
          Klartext sehen wir es nie. Rechtsgrundlage ist die Vertragserfüllung (Art. 6 Abs. 1 lit. b DSGVO).
        </p>
        <p>
          Bei der Registrierung und beim Passwortwechsel prüfen wir, ob das Passwort aus bekannten Datenlecks stammt. Dazu senden wir
          nur die ersten fünf Zeichen eines SHA-1-Hashwerts an den Dienst „Have I Been Pwned“ (k-Anonymität); weder Passwort noch
          E-Mail verlassen unseren Server. Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO (Schutz Ihres Kontos).
        </p>
      </Abschnitt>

      <Abschnitt titel="5. Cookies">
        <p>
          Wir setzen ein einziges, technisch notwendiges Cookie für die Anmeldung (<code>__Host-sk_sitzung</code>). Es enthält eine
          zufällige Kennung, ist für Skripte nicht lesbar und läuft spätestens nach 7 Tagen bzw. nach 24 Stunden Inaktivität ab.
          Rechtsgrundlage: § 25 Abs. 2 Nr. 2 TDDDG; eine Einwilligung ist nicht erforderlich.
        </p>
      </Abschnitt>

      <Abschnitt titel="6. Warteliste und Pilotvereine">
        <p>
          Wenn Sie sich auf der Startseite eintragen, speichern wir E-Mail-Adresse und – freiwillig – Verein und Rolle, um Sie zu
          Sponsorenkompass zu kontaktieren. Rechtsgrundlage ist Ihre Einwilligung (Art. 6 Abs. 1 lit. a DSGVO), die Sie jederzeit per
          E-Mail an {ANBIETER.email} widerrufen können. Wir löschen die Angaben nach Widerruf bzw. spätestens 12 Monate nach dem
          letzten Kontakt.
        </p>
      </Abschnitt>

      <Abschnitt titel="7. Potenzialanalyse – welche Daten wohin gehen">
        <p>Für die Analyse eines Vereins verarbeiten wir öffentlich zugängliche Informationen und nutzen folgende Dienste:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>Exa (Exa Labs, Inc., USA):</strong> Abruf und Durchsuchen öffentlicher Webseiten – der Vereinswebsite und der Websites von Unternehmen.</li>
          <li><strong>Google Gemini über Vertex AI (Google Cloud):</strong> Auswertung der gefundenen Texte, Erkennen von Sponsorenlogos, Bewertung und Formulieren von Anschreiben. Dabei werden Vereinsangaben und die gefundenen Texte übermittelt.</li>
          <li><strong>Google Places API (Google Cloud):</strong> Suche nach Betrieben im Umkreis der Sportstätte.</li>
          <li><strong>OpenStreetMap (Nominatim, Overpass):</strong> Umrechnung von Adressen in Koordinaten und Suche nach Betrieben, wenn Google nicht verfügbar ist.</li>
        </ul>
        <p>
          Übermittelt werden Inhalte, keine Kontodaten. Soweit Anbieter Daten außerhalb der EU verarbeiten, erfolgt dies auf Grundlage
          eines Angemessenheitsbeschlusses (EU-US Data Privacy Framework, soweit der Anbieter zertifiziert ist) oder von
          Standardvertragsklauseln. Rechtsgrundlage ist die Vertragserfüllung (Art. 6 Abs. 1 lit. b DSGVO).
        </p>
        <p>
          Zu Unternehmen verarbeiten wir nur öffentlich verfügbare Angaben (Name, Branche, Adresse, Website, öffentliche Berichte)
          und nennen zu jeder Aussage die Quelle. Ansprechpartner tragen Vereine selbst ein. Rechtsgrundlage ist das berechtigte
          Interesse der Vereine an der Sponsorengewinnung (Art. 6 Abs. 1 lit. f DSGVO). Sponsorenkompass versendet keine Nachrichten
          an Unternehmen; Vereine entscheiden und versenden selbst.
        </p>
      </Abschnitt>

      <Abschnitt titel="8. Karten und Logos">
        <p>
          Die Karte lädt Kartenbilder direkt von den Servern der OpenStreetMap Foundation; dabei wird Ihre IP-Adresse an diese
          übermittelt. Bei der Prüfung erkannter Sponsoren zeigen wir Logos, die von der Website Ihres Vereins geladen werden.
          Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO (Darstellung der Ergebnisse).
        </p>
      </Abschnitt>

      <Abschnitt titel="9. E-Mail-Benachrichtigung">
        <p>
          Wenn Sie es wünschen, informieren wir Sie per E-Mail, sobald eine Analyse fertig ist. Dafür nutzen wir die angegebene
          Adresse ausschließlich für diese Nachricht (Art. 6 Abs. 1 lit. b DSGVO).
        </p>
      </Abschnitt>

      <Abschnitt titel="10. Speicherdauer">
        <p>
          Kontodaten und Vereinsdaten speichern wir, solange das Konto besteht. Nach Löschung des Kontos entfernen wir die Daten,
          soweit keine gesetzlichen Aufbewahrungspflichten bestehen. Zwischengespeicherte Abrufe öffentlicher Webseiten löschen wir
          regelmäßig. Sitzungen enden nach den in Abschnitt 5 genannten Fristen.
        </p>
      </Abschnitt>

      <Abschnitt titel="11. Ihre Rechte">
        <p>
          Sie haben das Recht auf Auskunft (Art. 15), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung (Art. 18),
          Datenübertragbarkeit (Art. 20) und Widerspruch gegen Verarbeitungen auf Grundlage berechtigter Interessen (Art. 21 DSGVO).
          Erteilte Einwilligungen können Sie jederzeit für die Zukunft widerrufen. Eine E-Mail an {ANBIETER.email} genügt.
        </p>
        <p>Sie können sich außerdem bei einer Datenschutz-Aufsichtsbehörde beschweren, etwa bei: {AUFSICHT}.</p>
      </Abschnitt>

      <Abschnitt titel="12. Sicherheit">
        <p>
          Wir schützen Ihre Daten nach dem Stand der Technik: verschlüsselte Übertragung (HTTPS), Passwort-Hashing mit Argon2id,
          geschützte Sitzungscookies, Begrenzung von Anmeldeversuchen und eine strikte Trennung der Daten verschiedener Konten.
        </p>
      </Abschnitt>

      <Abschnitt titel="13. Keine automatisierten Entscheidungen">
        <p>
          Bewertungen und Vorschläge sind Hilfen für den Verein. Es findet keine automatisierte Entscheidung mit rechtlicher Wirkung
          gegenüber Personen statt (Art. 22 DSGVO).
        </p>
      </Abschnitt>
    </Seite>
  )
}
