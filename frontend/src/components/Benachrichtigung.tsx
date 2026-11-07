import { useState } from 'react'
import { api } from '../api'
import type { AnalyseZustand } from '../api'
import { Fehler, Knopf, Lader, eingabe } from './ui'

export default function Benachrichtigung({
  vereinId,
  zustand,
  kandidaten,
  onAenderung,
}: {
  vereinId: number
  zustand: AnalyseZustand
  kandidaten: number
  onAenderung: (z: AnalyseZustand) => void
}) {
  const [email, setEmail] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [sendet, setSendet] = useState(false)

  const r = zustand.recherche
  const geprueft = r.status.fertig ?? 0
  const inArbeit = (r.status.wartet ?? 0) + (r.status.laeuft ?? 0)
  const schritt =
    zustand.suche_status === 'fehler'
      ? null
      : kandidaten === 0
        ? 'Betriebe rund um eure Sportstätte werden gesucht …'
        : `${geprueft} von ${geprueft + inArbeit} Kandidaten mit Quellen geprüft …`

  async function eintragen(e: React.FormEvent) {
    e.preventDefault()
    setSendet(true)
    setFehler(null)
    try {
      onAenderung(await api.put<AnalyseZustand>(`/vereine/${vereinId}/benachrichtigung`, { email }))
    } catch (err) {
      setFehler((err as Error).message)
    } finally {
      setSendet(false)
    }
  }

  if (zustand.suche_status === 'fehler') {
    return <Fehler text={`Die Umkreissuche ist fehlgeschlagen: ${zustand.suche_fehler ?? 'unbekannter Fehler'}`} />
  }

  return (
    <section className="rounded-md border border-rasen-200 bg-rasen-50/60 p-4 sm:p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>{schritt && <Lader text={schritt} />}</div>
        {zustand.email_verfuegbar &&
          (zustand.benachrichtigung_email ? (
            <p className="text-sm text-rasen-900">
              Wir schicken das Ergebnis an <strong>{zustand.benachrichtigung_email}</strong>, sobald alles fertig ist.
            </p>
          ) : (
            <form onSubmit={eintragen} className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <span className="text-sm text-stein-700">Nicht warten?</span>
              <input
                type="email"
                required
                className={`${eingabe} sm:w-64`}
                placeholder="E-Mail für die Fertig-Meldung"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <Knopf type="submit" disabled={sendet}>Benachrichtigen</Knopf>
            </form>
          ))}
      </div>
      <Fehler text={fehler} />
    </section>
  )
}
