import { useEffect, useState } from 'react'
import { api, tokenLesen, tokenSetzen } from '../api'
import type { Konto } from '../api'
import { Fehler, Feld, Karte, Knopf, eingabe } from '../components/ui'

type VereinKurz = { id: number; name: string; ort: string; spielklasse: string | null }

export default function KontoSeite({ onVerein, onStart }: { onVerein: (id: number) => void; onStart: () => void }) {
  const [konto, setKonto] = useState<Konto | null>(null)
  const [vereine, setVereine] = useState<VereinKurz[]>([])
  const [modus, setModus] = useState<'anmelden' | 'registrieren'>('anmelden')
  const [email, setEmail] = useState('')
  const [passwort, setPasswort] = useState('')
  const [name, setName] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  async function laden() {
    if (!tokenLesen()) return setKonto(null)
    try {
      setKonto(await api.get<Konto>('/konto/ich'))
      setVereine(await api.get<VereinKurz[]>('/konto/vereine'))
    } catch {
      tokenSetzen(null)
      setKonto(null)
    }
  }

  useEffect(() => { laden() }, [])

  async function absenden(e: React.FormEvent) {
    e.preventDefault()
    setFehler(null)
    try {
      const r = await api.post<{ token: string; konto: Konto }>(`/konto/${modus}`, { email, passwort, name: name || null })
      tokenSetzen(r.token)
      setPasswort('')
      laden()
    } catch (err) {
      setFehler((err as Error).message)
    }
  }

  async function abmelden() {
    await api.post('/konto/abmelden').catch(() => null)
    tokenSetzen(null)
    setKonto(null)
    setVereine([])
  }

  if (konto) {
    return (
      <div className="mx-auto max-w-2xl space-y-5">
        <div className="flex items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Mein Konto</h1>
            <p className="text-slate-600">{konto.name ? `${konto.name} · ` : ''}{konto.email}</p>
          </div>
          <Knopf art="leise" onClick={abmelden}>Abmelden</Knopf>
        </div>
        <Karte titel="Meine Vereine">
          <ul className="divide-y divide-slate-100">
            {vereine.map((v) => (
              <li key={v.id}>
                <button onClick={() => onVerein(v.id)} className="flex w-full justify-between py-3 text-left text-sm hover:bg-slate-50">
                  <span className="font-medium text-slate-900">{v.name}</span>
                  <span className="text-slate-500">{v.ort}{v.spielklasse ? ` · ${v.spielklasse}` : ''}</span>
                </button>
              </li>
            ))}
            {vereine.length === 0 && <li className="py-3 text-sm text-slate-500">Noch kein Verein im Konto.</li>}
          </ul>
          <div className="mt-3"><Knopf onClick={onStart}>Neue Potenzialanalyse</Knopf></div>
        </Karte>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-semibold text-slate-900">{modus === 'anmelden' ? 'Anmelden' : 'Konto anlegen'}</h1>
      <p className="text-slate-600">Mit Konto bleiben eure Analysen, Sponsoren und Assets gespeichert und sind nur für euch sichtbar.</p>
      <Karte>
        <form onSubmit={absenden} className="space-y-3">
          {modus === 'registrieren' && <Feld label="Name (optional)"><input className={eingabe} value={name} onChange={(e) => setName(e.target.value)} /></Feld>}
          <Feld label="E-Mail"><input type="email" required autoComplete="email" className={eingabe} value={email} onChange={(e) => setEmail(e.target.value)} /></Feld>
          <Feld label="Passwort" hinweis={modus === 'registrieren' ? 'Mindestens 8 Zeichen.' : undefined}>
            <input type="password" required minLength={modus === 'registrieren' ? 8 : undefined}
              autoComplete={modus === 'registrieren' ? 'new-password' : 'current-password'}
              className={eingabe} value={passwort} onChange={(e) => setPasswort(e.target.value)} />
          </Feld>
          <Knopf type="submit">{modus === 'anmelden' ? 'Anmelden' : 'Konto anlegen'}</Knopf>
          <Fehler text={fehler} />
        </form>
      </Karte>
      <button className="text-sm text-teal-800 underline" onClick={() => { setModus(modus === 'anmelden' ? 'registrieren' : 'anmelden'); setFehler(null) }}>
        {modus === 'anmelden' ? 'Noch kein Konto? Jetzt anlegen' : 'Schon ein Konto? Anmelden'}
      </button>
    </div>
  )
}
