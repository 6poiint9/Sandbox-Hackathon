import { useEffect, useState } from 'react'
import { api } from './api'
import type { Konto } from './api'
import Analyse from './views/Analyse'
import Assets from './views/Assets'
import Detail from './views/Detail'
import KontoSeite, { Anmeldung } from './views/KontoSeite'
import Landing from './views/Landing'
import Onboarding from './views/Onboarding'
import { Datenschutz, Impressum } from './views/Rechtliches'
import Sponsoren from './views/Sponsoren'

// Einfache Hash-Navigation: #/ · #/verein/1 · #/verein/1/kandidat/5 · #/verein/1/sponsoren
type Ansicht =
  | { art: 'landing' }
  | { art: 'konto' }
  | { art: 'impressum' }
  | { art: 'datenschutz' }
  | { art: 'start' }
  | { art: 'analyse'; verein: number }
  | { art: 'detail'; verein: number; kandidat: number }
  | { art: 'sponsoren'; verein: number }
  | { art: 'assets'; verein: number }

function lesen(): Ansicht {
  const teile = window.location.hash.replace(/^#\/?/, '').split('/')
  const verein = Number(teile[1])
  if (teile[0] === 'start') return { art: 'start' }
  if (teile[0] === 'konto') return { art: 'konto' }
  if (teile[0] === 'impressum') return { art: 'impressum' }
  if (teile[0] === 'datenschutz') return { art: 'datenschutz' }
  if (teile[0] !== 'verein' || !verein) return { art: 'landing' }
  if (teile[2] === 'kandidat' && Number(teile[3])) return { art: 'detail', verein, kandidat: Number(teile[3]) }
  if (teile[2] === 'sponsoren') return { art: 'sponsoren', verein }
  if (teile[2] === 'assets') return { art: 'assets', verein }
  return { art: 'analyse', verein }
}

const gehe = (pfad: string) => {
  window.location.hash = pfad
  window.scrollTo(0, 0)
}

export default function App() {
  const [ansicht, setAnsicht] = useState<Ansicht>(lesen)
  const [konto, setKonto] = useState<Konto | null>(null)
  const [geprueft, setGeprueft] = useState(false)

  useEffect(() => {
    const aktualisieren = () => setAnsicht(lesen())
    const konto = () =>
      api.get<Konto>('/konto/ich').then(setKonto).catch(() => setKonto(null)).finally(() => setGeprueft(true))
    konto()
    window.addEventListener('hashchange', aktualisieren)
    window.addEventListener('konto-geaendert', konto)
    return () => {
      window.removeEventListener('hashchange', aktualisieren)
      window.removeEventListener('konto-geaendert', konto)
    }
  }, [])

  const verein = 'verein' in ansicht ? ansicht.verein : null
  const braucht_anmeldung = !['landing', 'konto', 'impressum', 'datenschutz'].includes(ansicht.art)

  return (
    <div className="min-h-screen">
      <header className="border-b border-linie bg-kreide">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <button onClick={() => gehe('/')} className="flex items-center gap-2 font-tafel text-2xl font-bold text-tafel">
            <span aria-hidden="true" className="inline-block h-5 w-3 -skew-x-12 bg-signal-400" />
            Sponsorenkompass
          </button>
          {verein && konto && (
            <nav className="flex gap-4 text-[15px]">
              <NavLink aktiv={ansicht.art === 'analyse' || ansicht.art === 'detail'} onClick={() => gehe(`/verein/${verein}`)}>Potenzialanalyse</NavLink>
              <NavLink aktiv={ansicht.art === 'sponsoren'} onClick={() => gehe(`/verein/${verein}/sponsoren`)}>Sponsoren</NavLink>
              <NavLink aktiv={ansicht.art === 'assets'} onClick={() => gehe(`/verein/${verein}/assets`)}>Assets</NavLink>
            </nav>
          )}
          <span className="ml-auto hidden text-xs text-stein-500 sm:block">Der Sponsor um die Ecke: gefunden, begründet, angesprochen.</span>
          <div className="ml-auto flex items-center gap-2 sm:ml-0">
            <button onClick={() => gehe('/konto')} className="px-2 py-1.5 text-sm font-medium text-stein-700 underline-offset-4 hover:underline">
              {konto ? 'Mein Konto' : 'Anmelden'}
            </button>
            {!verein && ansicht.art === 'landing' && (
              <button onClick={() => gehe('/start')} className="rounded-[4px] bg-signal-400 px-3 py-1.5 text-sm font-semibold text-tinte hover:bg-signal-300">Ausprobieren</button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
        {ansicht.art === 'landing' && <Landing onStart={() => gehe('/start')} />}
        {ansicht.art === 'impressum' && <Impressum />}
        {ansicht.art === 'datenschutz' && <Datenschutz />}
        {ansicht.art === 'konto' && geprueft && <KontoSeite konto={konto} onVerein={(id) => gehe(`/verein/${id}`)} onStart={() => gehe('/start')} />}
        {braucht_anmeldung && geprueft && !konto && (
          <Anmeldung
            hinweis={ansicht.art === 'start' ? 'Bitte meldet euch an oder legt kostenlos ein Konto an – dann startet die Potenzialanalyse. Eure Daten sind nur für euch sichtbar.' : 'Bitte anmelden, um diesen Verein zu sehen.'}
            onAngemeldet={setKonto}
          />
        )}
        {ansicht.art === 'start' && konto && <Onboarding onFertig={(id) => gehe(`/verein/${id}`)} />}
        {ansicht.art === 'analyse' && konto && (
          <Analyse vereinId={ansicht.verein} onOeffnen={(k) => gehe(`/verein/${ansicht.verein}/kandidat/${k}`)} />
        )}
        {ansicht.art === 'detail' && konto && (
          <Detail vereinId={ansicht.verein} kandidatId={ansicht.kandidat} onZurueck={() => gehe(`/verein/${ansicht.verein}`)} />
        )}
        {ansicht.art === 'assets' && konto && <Assets vereinId={ansicht.verein} />}
        {ansicht.art === 'sponsoren' && konto && (
          <Sponsoren vereinId={ansicht.verein} onOeffnen={(k) => gehe(`/verein/${ansicht.verein}/kandidat/${k}`)} />
        )}
      </main>

      <footer className="border-t border-linie bg-kreide px-4 py-6 text-center text-xs text-stein-500">
        <a className="hover:text-stein-800" href="#/impressum">Impressum</a>
        <span className="mx-2">·</span>
        <a className="hover:text-stein-800" href="#/datenschutz">Datenschutz</a>
        <span className="mx-2">·</span>
        Sponsorenkompass – entstanden beim Cursor × Sandbox Founders Hackathon, Stuttgart 2026
      </footer>
    </div>
  )
}

function NavLink({ aktiv, onClick, children }: { aktiv: boolean; onClick: () => void; children: string }) {
  return (
    <button onClick={onClick} className={`border-b-[3px] py-1.5 ${aktiv ? 'border-signal-400 font-semibold text-tinte' : 'border-transparent text-stein-600 hover:text-tinte'}`}>
      {children}
    </button>
  )
}
