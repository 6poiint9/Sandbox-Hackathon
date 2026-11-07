import { useEffect, useState } from 'react'
import { api } from '../api'
import { Fehler, Knopf, eingabe } from '../components/ui'

type Zaehler = { anmeldungen: number; pilotvereine: number }

const SCHRITTE = [
  ['Website eingeben', 'Wir lesen Mannschaften, Spielklassen, Sportstätte und eure Sponsoren aus – auch die, die nur als Logo auftauchen.'],
  ['Potenzial sehen', 'Was ihr anbieten könnt, was davon frei ist und was es wert ist – als Spanne pro Saison mit nachvollziehbaren Richtwerten.'],
  ['Passende Betriebe', 'Unternehmen rund um eure Sportstätte, die noch kein Sponsor sind – jeder Vorschlag mit drei Gründen und Quellenlinks.'],
  ['Persönlich ansprechen', 'Fertiger Brief, Telefonleitfaden und E-Mail für nach dem Gespräch – mit echtem Bezug zum Unternehmen.'],
]

const FUNKTIONEN = [
  ['Potenzialanalyse', 'Ungenutztes Sponsoring in Euro, freie Pakete, Lücken nach Branchen.'],
  ['Kandidaten mit Quellen', 'Karte und Liste, Bewertung 0–100, jede Aussage belegt – nichts erfunden.'],
  ['Ansprache auf Knopfdruck', 'Brief, Leitfaden und E-Mail, die auf das Unternehmen eingehen.'],
  ['Sponsoren-CRM', 'Bestand, Verlauf, Wiedervorlagen und auslaufende Verträge im Blick.'],
  ['Assets verwalten', 'Banden, Trikots, Social Media: wie viel vergeben ist, an wen, bis wann.'],
  ['Kein Massenversand', 'Ihr entscheidet und versendet selbst – Brief und Anruf zuerst.'],
]

export default function Landing({ onStart }: { onStart: () => void }) {
  const [email, setEmail] = useState('')
  const [verein, setVerein] = useState('')
  const [rolle, setRolle] = useState('')
  const [pilot, setPilot] = useState(true)
  const [einwilligung, setEinwilligung] = useState(false)
  const [zaehler, setZaehler] = useState<Zaehler | null>(null)
  const [fertig, setFertig] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

  useEffect(() => {
    api.get<Zaehler>('/interessenten/anzahl').then(setZaehler).catch(() => null)
  }, [])

  async function anmelden(e: React.FormEvent) {
    e.preventDefault()
    setFehler(null)
    try {
      setZaehler(await api.post<Zaehler>('/interessenten', { email, verein: verein || null, rolle: rolle || null, pilot }))
      setFertig(true)
    } catch (err) {
      setFehler((err as Error).message)
    }
  }

  return (
    <div className="-mx-4 -my-6 sm:-my-8">
      {/* Hero */}
      <section className="bg-tafel px-4 py-14 text-kreide sm:py-20">
        <div className="mx-auto max-w-4xl">
          <h1 className="max-w-3xl text-4xl font-bold leading-[1.05] text-white sm:text-6xl">Neue Sponsoren statt neuer Excel-Listen.</h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-kreide/85">
            Für Sportvereine und Fördervereine: Sponsorenkompass zeigt euch in wenigen Minuten, wie viel Sponsoring-Potenzial in eurem Verein steckt, welche Betriebe um die Ecke passen – und wie ihr sie persönlich ansprecht.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <button onClick={onStart} className="rounded-[4px] bg-signal-400 px-5 py-3 font-semibold text-tinte hover:bg-signal-300">Kostenlos ausprobieren</button>
            <a href="#anmelden" onClick={(e) => { e.preventDefault(); document.getElementById('anmelden')?.scrollIntoView({ behavior: 'smooth' }) }}
              className="rounded-[4px] border border-kreide/40 px-5 py-3 text-center font-semibold text-white hover:border-kreide">Pilotverein werden</a>
          </div>
          <p className="mt-6 text-sm text-kreide/65">Nur die Vereinswebsite eingeben – kein Konto nötig.</p>
        </div>
      </section>

      {/* Problem */}
      <section className="px-4 py-14">
        <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-3">
          {[
            ['Klinkenputzen im Ehrenamt', 'Sponsorensuche läuft über Branchenbuch und Bauchgefühl – nach Feierabend, ohne Vertriebserfahrung.'],
            ['Massenbriefe ohne Bezug', 'Allgemeine Anfragen landen im Papierkorb. Wer nicht weiß, was einen Betrieb bewegt, bekommt selten eine Antwort.'],
            ['Unklarer Wert', 'Was ist eine Bande wert, was ein Trikot? Viele Vereine verkaufen sich unter Wert – oder gar nicht.'],
          ].map(([t, x]) => (
            <div key={t}>
              <h3 className="text-xl font-semibold text-tinte">{t}</h3>
              <p className="mt-2 text-sm text-stein-600">{x}</p>
            </div>
          ))}
        </div>
      </section>

      {/* So funktioniert's */}
      <section className="bg-white px-4 py-14">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-3xl font-semibold text-tinte">So funktioniert's</h2>
          <ol className="mt-8 grid gap-6 md:grid-cols-4">
            {SCHRITTE.map(([t, x], i) => (
              <li key={t}>
                <span className="flex h-10 w-10 items-center justify-center rounded-[3px] bg-tafel font-tafel text-2xl font-bold text-signal-400">{i + 1}</span>
                <h3 className="mt-3 text-xl font-semibold text-tinte">{t}</h3>
                <p className="mt-1 text-sm text-stein-600">{x}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Funktionen */}
      <section className="px-4 py-14">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-3xl font-semibold text-tinte">Alles für die Sponsorengewinnung an einem Ort</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FUNKTIONEN.map(([t, x]) => (
              <div key={t} className="border-t-[3px] border-tafel bg-white p-5">
                <h3 className="text-xl font-semibold text-tinte">{t}</h3>
                <p className="mt-1 text-sm text-stein-600">{x}</p>
              </div>
            ))}
          </div>
          <p className="mt-6 text-sm text-stein-500">
            Unterschied zu Sponsoring-Marktplätzen: Die warten, bis sich Unternehmen selbst anmelden. Sponsorenkompass sucht aktiv die Betriebe, die euren Verein noch nicht kennen.
          </p>
        </div>
      </section>

      {/* Anmeldung */}
      <section id="anmelden" className="bg-white px-4 py-14">
        <div className="mx-auto max-w-xl">
          <h2 className="text-3xl font-semibold text-tinte">Pilotverein werden</h2>
          <p className="mt-2 text-stein-600">
            In der Pilotphase kostenlos. Wir richten Sponsorenkompass mit euch ein und lernen von euren Erfahrungen.
            {zaehler && zaehler.anmeldungen > 0 && <> Bereits <strong>{zaehler.anmeldungen}</strong> {zaehler.anmeldungen === 1 ? 'Anmeldung' : 'Anmeldungen'}.</>}
          </p>
          {fertig ? (
            <p className="mt-6 border-l-4 border-rasen-600 bg-rasen-50 px-4 py-3 text-rasen-900">Danke! Wir melden uns in den nächsten Tagen bei euch.</p>
          ) : (
            <form onSubmit={anmelden} className="mt-6 space-y-3">
              <input type="email" required className={eingabe} placeholder="E-Mail" value={email} onChange={(e) => setEmail(e.target.value)} />
              <input className={eingabe} placeholder="Verein (optional)" value={verein} onChange={(e) => setVerein(e.target.value)} />
              <select className={eingabe} value={rolle} onChange={(e) => setRolle(e.target.value)}>
                <option value="">Eure Rolle (optional)</option>
                <option>Vorstand</option>
                <option>Kassenwart</option>
                <option>Sponsoring-Verantwortliche</option>
                <option>Verband / Sportkreis</option>
                <option>Sonstiges</option>
              </select>
              <label className="flex items-center gap-2 text-sm text-stein-700">
                <input type="checkbox" className="accent-rasen-700" checked={pilot} onChange={(e) => setPilot(e.target.checked)} />
                Wir möchten als Pilotverein mitmachen
              </label>
              <label className="flex items-start gap-2 text-xs text-stein-600">
                <input type="checkbox" required className="mt-0.5 accent-rasen-700" checked={einwilligung} onChange={(e) => setEinwilligung(e.target.checked)} />
                <span>
                  Ich willige ein, dass Sponsorenkompass meine Angaben speichert, um mich zum Angebot zu kontaktieren. Widerruf jederzeit per
                  E-Mail. Details in der <a className="text-rasen-800 underline" href="#/datenschutz">Datenschutzerklärung</a>.
                </span>
              </label>
              <Knopf type="submit" disabled={!einwilligung}>Anmelden</Knopf>
              <Fehler text={fehler} />
            </form>
          )}
        </div>
      </section>

    </div>
  )
}
