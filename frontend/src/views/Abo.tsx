import { useState } from 'react'
import { api } from '../api'
import type { Konto } from '../api'
import { Fehler, Karte, Knopf } from '../components/ui'
import { Anmeldung } from './KontoSeite'

// Demo-Abo: zeigt das Geschäftsmodell, ohne echte Zahlung (README: Bezahlung nicht im MVP).
const PREIS = '29 €'
const LEISTUNGEN = [
  'Alle passenden Betriebe im Umkreis statt nur der ersten drei',
  'Recherche mit Quellen und Paket-Empfehlung für jeden Betrieb',
  'Brief, Gesprächsleitfaden und E-Mail für jeden Betrieb',
  'Export der Kandidaten als CSV',
]

export default function Abo({
  konto,
  onKonto,
  onFertig,
}: {
  konto: Konto | null
  onKonto: (k: Konto) => void
  onFertig: () => void
}) {
  const [sendet, setSendet] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)

  async function aktivieren() {
    setSendet(true)
    setFehler(null)
    try {
      onKonto(await api.post<Konto>('/konto/abo', { aktiv: true }))
      onFertig()
    } catch (err) {
      setFehler((err as Error).message)
    } finally {
      setSendet(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-4xl gap-6 md:grid-cols-[1.1fr_1fr]">
      <Karte titel="Alle Betriebe freischalten">
        <p className="font-tafel text-5xl font-bold text-tafel">
          {PREIS}
          <span className="ml-2 font-sans text-base font-medium text-stein-600">pro Monat, monatlich kündbar</span>
        </p>
        <ul className="mt-5 space-y-2 text-[15px]">
          {LEISTUNGEN.map((l) => (
            <li key={l} className="flex gap-3">
              <span aria-hidden="true" className="mt-2 h-2 w-2 shrink-0 bg-signal-400" />
              {l}
            </li>
          ))}
        </ul>
        <p className="mt-5 border-l-4 border-signal-400 bg-signal-50 px-3 py-2 text-sm text-stein-700">
          Demo: Es wird nichts berechnet. In der Pilotphase ist das Abo kostenlos.
        </p>
      </Karte>

      <div>
        {konto ? (
          konto.abo ? (
            <Karte titel="Abo ist aktiv">
              <p className="text-[15px] text-stein-700">Alle Betriebe sind für euch freigeschaltet.</p>
              <div className="mt-4"><Knopf onClick={onFertig}>Zur Potenzialanalyse</Knopf></div>
            </Karte>
          ) : (
            <Karte titel="Abo aktivieren">
              <p className="mb-4 text-[15px] text-stein-700">Angemeldet als {konto.email}.</p>
              <Knopf art="signal" onClick={aktivieren} disabled={sendet}>
                {sendet ? 'Wird aktiviert …' : `Abo für ${PREIS} aktivieren`}
              </Knopf>
              <div className="mt-3"><Fehler text={fehler} /></div>
            </Karte>
          )
        ) : (
          <Anmeldung
            hinweis="Legt ein kostenloses Konto an, dann schaltet ihr das Abo frei. Euer Verein und die bisherigen Ergebnisse werden übernommen."
            onAngemeldet={onKonto}
          />
        )}
      </div>
    </div>
  )
}
