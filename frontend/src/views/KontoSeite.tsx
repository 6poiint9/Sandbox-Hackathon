import { useEffect, useState } from 'react'
import { api, kontoGeaendert } from '../api'
import type { Konto } from '../api'
import { Fehler, Feld, Karte, Knopf, eingabe } from '../components/ui'

type VereinKurz = { id: number; name: string; ort: string; spielklasse: string | null }

function PasswortFeld({ wert, setWert, neu, label = 'Passwort' }: { wert: string; setWert: (v: string) => void; neu: boolean; label?: string }) {
  const [sichtbar, setSichtbar] = useState(false)
  return (
    <Feld label={label} hinweis={neu ? 'Mindestens 12 Zeichen. Am besten mehrere Wörter, z. B. „Tor-Bratwurst-Flutlicht-Elz“.' : undefined}>
      <div className="flex gap-2">
        <input type={sichtbar ? 'text' : 'password'} required minLength={neu ? 12 : undefined} maxLength={256}
          autoComplete={neu ? 'new-password' : 'current-password'} className={eingabe} value={wert} onChange={(e) => setWert(e.target.value)} />
        <button type="button" className="shrink-0 rounded-lg border border-slate-300 px-3 text-xs text-slate-600 hover:bg-slate-50"
          onClick={() => setSichtbar(!sichtbar)} aria-label={sichtbar ? 'Passwort verbergen' : 'Passwort anzeigen'}>
          {sichtbar ? 'Verbergen' : 'Zeigen'}
        </button>
      </div>
    </Feld>
  )
}

export function Anmeldung({ hinweis, onAngemeldet }: { hinweis?: string; onAngemeldet: (k: Konto) => void }) {
  const [modus, setModus] = useState<'anmelden' | 'registrieren'>('registrieren')
  const [email, setEmail] = useState('')
  const [passwort, setPasswort] = useState('')
  const [name, setName] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [sendet, setSendet] = useState(false)

  async function absenden(e: React.FormEvent) {
    e.preventDefault()
    setFehler(null)
    setSendet(true)
    try {
      const k = await api.post<Konto>(`/konto/${modus}`, modus === 'registrieren' ? { email, passwort, name: name || null } : { email, passwort })
      setPasswort('')
      kontoGeaendert()
      onAngemeldet(k)
    } catch (err) {
      setFehler((err as Error).message)
    } finally {
      setSendet(false)
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-semibold text-slate-900">{modus === 'anmelden' ? 'Anmelden' : 'Konto anlegen'}</h1>
      <p className="text-slate-600">{hinweis ?? 'Mit Konto bleiben eure Analysen, Sponsoren und Assets gespeichert und sind nur für euch sichtbar.'}</p>
      <Karte>
        <form onSubmit={absenden} className="space-y-3">
          {modus === 'registrieren' && <Feld label="Name (optional)"><input className={eingabe} autoComplete="name" maxLength={100} value={name} onChange={(e) => setName(e.target.value)} /></Feld>}
          <Feld label="E-Mail"><input type="email" required autoComplete="email" maxLength={254} className={eingabe} value={email} onChange={(e) => setEmail(e.target.value)} /></Feld>
          <PasswortFeld wert={passwort} setWert={setPasswort} neu={modus === 'registrieren'} />
          <Knopf type="submit" disabled={sendet}>{modus === 'anmelden' ? 'Anmelden' : 'Konto anlegen'}</Knopf>
          <Fehler text={fehler} />
        </form>
      </Karte>
      <button className="text-sm text-teal-800 underline" onClick={() => { setModus(modus === 'anmelden' ? 'registrieren' : 'anmelden'); setFehler(null) }}>
        {modus === 'anmelden' ? 'Noch kein Konto? Jetzt anlegen' : 'Schon ein Konto? Anmelden'}
      </button>
      {modus === 'registrieren' && (
        <p className="text-xs text-slate-500">
          Mit dem Anlegen des Kontos gilt unsere <a className="text-teal-800 underline" href="#/datenschutz">Datenschutzerklärung</a>.
        </p>
      )}
      <p className="text-xs text-slate-500">
        Sicherheit: Passwörter speichern wir nur als Argon2id-Hash und prüfen sie anonym gegen bekannte Datenlecks. Die Sitzung liegt in einem geschützten Cookie, das kein Skript lesen kann.
      </p>
    </div>
  )
}

export default function KontoSeite({ konto, onVerein, onStart }: { konto: Konto | null; onVerein: (id: number) => void; onStart: () => void }) {
  const [vereine, setVereine] = useState<VereinKurz[]>([])
  const [altPw, setAltPw] = useState('')
  const [neuPw, setNeuPw] = useState('')
  const [meldung, setMeldung] = useState<string | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)

  useEffect(() => {
    if (konto) api.get<VereinKurz[]>('/konto/vereine').then(setVereine).catch(() => setVereine([]))
  }, [konto])

  if (!konto) return <Anmeldung onAngemeldet={() => null} />

  async function abmelden(ueberall: boolean) {
    await api.post(ueberall ? '/konto/ueberall-abmelden' : '/konto/abmelden').catch(() => null)
    kontoGeaendert()
  }

  async function passwortAendern(e: React.FormEvent) {
    e.preventDefault()
    setFehler(null)
    setMeldung(null)
    try {
      await api.post('/konto/passwort', { altes_passwort: altPw, neues_passwort: neuPw })
      setAltPw('')
      setNeuPw('')
      setMeldung('Passwort geändert. Alle anderen Geräte wurden abgemeldet.')
    } catch (err) {
      setFehler((err as Error).message)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Mein Konto</h1>
          <p className="text-slate-600">{konto.name ? `${konto.name} · ` : ''}{konto.email}</p>
        </div>
        <div className="flex gap-1">
          <Knopf art="leise" onClick={() => abmelden(false)}>Abmelden</Knopf>
          <Knopf art="leise" onClick={() => abmelden(true)}>Auf allen Geräten abmelden</Knopf>
        </div>
      </div>
      <Karte titel="Meine Vereine">
        <ul className="divide-y divide-slate-100">
          {vereine.map((v) => (
            <li key={v.id}>
              <button onClick={() => onVerein(v.id)} className="flex w-full justify-between gap-3 py-3 text-left text-sm hover:bg-slate-50">
                <span className="font-medium text-slate-900">{v.name}</span>
                <span className="text-slate-500">{v.ort}{v.spielklasse ? ` · ${v.spielklasse}` : ''}</span>
              </button>
            </li>
          ))}
          {vereine.length === 0 && <li className="py-3 text-sm text-slate-500">Noch kein Verein im Konto.</li>}
        </ul>
        <div className="mt-3"><Knopf onClick={onStart}>Neue Potenzialanalyse</Knopf></div>
      </Karte>
      <Karte titel="Passwort ändern">
        <form onSubmit={passwortAendern} className="space-y-3">
          <PasswortFeld wert={altPw} setWert={setAltPw} neu={false} label="Bisheriges Passwort" />
          <PasswortFeld wert={neuPw} setWert={setNeuPw} neu label="Neues Passwort" />
          <Knopf type="submit" art="sekundaer">Passwort ändern</Knopf>
          {meldung && <p className="text-sm text-teal-800">{meldung}</p>}
          <Fehler text={fehler} />
        </form>
      </Karte>
    </div>
  )
}
