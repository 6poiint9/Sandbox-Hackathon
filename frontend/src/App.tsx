import { useEffect, useState } from 'react'
import { tokenLesen } from './api'
import Analyse from './views/Analyse'
import Assets from './views/Assets'
import Detail from './views/Detail'
import KontoSeite from './views/KontoSeite'
import Landing from './views/Landing'
import Onboarding from './views/Onboarding'
import Sponsoren from './views/Sponsoren'

// Einfache Hash-Navigation: #/ · #/verein/1 · #/verein/1/kandidat/5 · #/verein/1/sponsoren
type Ansicht =
  | { art: 'landing' }
  | { art: 'konto' }
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
  const [angemeldet, setAngemeldet] = useState(() => !!tokenLesen())

  useEffect(() => {
    const aktualisieren = () => setAnsicht(lesen())
    const konto = () => setAngemeldet(!!tokenLesen())
    window.addEventListener('hashchange', aktualisieren)
    window.addEventListener('konto-geaendert', konto)
    return () => {
      window.removeEventListener('hashchange', aktualisieren)
      window.removeEventListener('konto-geaendert', konto)
    }
  }, [])

  const verein = 'verein' in ansicht ? ansicht.verein : null

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <button onClick={() => gehe('/')} className="flex items-center gap-2 font-semibold text-slate-900">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-teal-700 text-white">✦</span>
            Sponsorenkompass
          </button>
          {verein && (
            <nav className="flex gap-1 text-sm">
              <NavLink aktiv={ansicht.art === 'analyse' || ansicht.art === 'detail'} onClick={() => gehe(`/verein/${verein}`)}>Potenzialanalyse</NavLink>
              <NavLink aktiv={ansicht.art === 'sponsoren'} onClick={() => gehe(`/verein/${verein}/sponsoren`)}>Sponsoren</NavLink>
              <NavLink aktiv={ansicht.art === 'assets'} onClick={() => gehe(`/verein/${verein}/assets`)}>Assets</NavLink>
            </nav>
          )}
          <span className="ml-auto hidden text-xs text-slate-500 sm:block">Der Sponsor um die Ecke: gefunden, begründet, angesprochen.</span>
          <div className="ml-auto flex items-center gap-2 sm:ml-0">
            <button onClick={() => gehe('/konto')} className="rounded-lg px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100">
              {angemeldet ? 'Mein Konto' : 'Anmelden'}
            </button>
            {!verein && ansicht.art === 'landing' && (
              <button onClick={() => gehe('/start')} className="rounded-lg bg-teal-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-800">Ausprobieren</button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
        {ansicht.art === 'landing' && <Landing onStart={() => gehe('/start')} />}
        {ansicht.art === 'konto' && <KontoSeite onVerein={(id) => gehe(`/verein/${id}`)} onStart={() => gehe('/start')} />}
        {ansicht.art === 'start' && <Onboarding onFertig={(id) => gehe(`/verein/${id}`)} />}
        {ansicht.art === 'analyse' && (
          <Analyse vereinId={ansicht.verein} onOeffnen={(k) => gehe(`/verein/${ansicht.verein}/kandidat/${k}`)} />
        )}
        {ansicht.art === 'detail' && (
          <Detail vereinId={ansicht.verein} kandidatId={ansicht.kandidat} onZurueck={() => gehe(`/verein/${ansicht.verein}`)} />
        )}
        {ansicht.art === 'assets' && <Assets vereinId={ansicht.verein} />}
        {ansicht.art === 'sponsoren' && (
          <Sponsoren vereinId={ansicht.verein} onOeffnen={(k) => gehe(`/verein/${ansicht.verein}/kandidat/${k}`)} />
        )}
      </main>
    </div>
  )
}

function NavLink({ aktiv, onClick, children }: { aktiv: boolean; onClick: () => void; children: string }) {
  return (
    <button onClick={onClick} className={`rounded-md px-3 py-1.5 ${aktiv ? 'bg-teal-50 font-medium text-teal-900' : 'text-slate-600 hover:bg-slate-100'}`}>
      {children}
    </button>
  )
}
