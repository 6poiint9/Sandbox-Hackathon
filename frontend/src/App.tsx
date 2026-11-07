import { useEffect, useState } from 'react'
import { apiGet } from './api'

type Health = { status: string; demo_mode: boolean; exa_konfiguriert: boolean; katalog_eintraege: number }

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)

  useEffect(() => {
    apiGet<Health>('/health').then(setHealth).catch((e: Error) => setFehler(e.message))
  }, [])

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-3xl font-semibold text-slate-900">Sponsorenkompass</h1>
      <p className="mt-2 text-slate-600">Der Sponsor um die Ecke: gefunden, begründet, angesprochen.</p>
      <section className="mt-8 rounded-lg border border-slate-200 bg-white p-4 text-sm">
        {fehler && <p className="text-red-700">Backend nicht erreichbar: {fehler}</p>}
        {!fehler && !health && <p>Verbinde mit dem Backend …</p>}
        {health && (
          <ul className="space-y-1">
            <li>Backend: <span className="font-medium text-akzent">{health.status}</span></li>
            <li>Exa-Key: {health.exa_konfiguriert ? 'eingetragen' : 'fehlt in backend/.env'}</li>
            <li>Demo-Modus: {health.demo_mode ? 'an' : 'aus'}</li>
            <li>Katalog: {health.katalog_eintraege} Sponsoring-Möglichkeiten</li>
          </ul>
        )}
      </section>
    </main>
  )
}
