import { useMemo } from 'react'
import type { KatalogEintrag } from '../api'
import { eingabe } from './ui'

/** Eine Leistung des Vereins im Onboarding: vorhanden? wie viele? davon vergeben? */
export type Leistung = { haben: boolean; anzahl: number; vergeben: number }
export const LEER: Leistung = { haben: false, anzahl: 1, vergeben: 0 }

export function leistungKorrigieren(l: Leistung): Leistung {
  const anzahl = Math.max(1, Math.min(999, Math.round(l.anzahl) || 1))
  return { ...l, anzahl, vergeben: Math.max(0, Math.min(anzahl, Math.round(l.vergeben) || 0)) }
}

const EINHEIT: Record<string, string> = { saison: 'Saison', je_spiel: 'Spiel', je_satz: 'Satz', je_turnier: 'Turnier', je_mitglied: 'Mitglied' }
const euro = (n: number) => n.toLocaleString('de-DE') + ' €'

export function richtwertText(e: KatalogEintrag) {
  if (e.preis_min == null || e.preis_max == null) return 'Sachleistung'
  return `${euro(e.preis_min)}–${euro(e.preis_max)} je ${EINHEIT[e.einheit] ?? 'Saison'}`
}

/** Zahlenfeld mit −/+ – gut bedienbar auch auf dem Handy. */
export function Stepper({ wert, min, max, label, onAendern }: { wert: number; min: number; max: number; label: string; onAendern: (n: number) => void }) {
  const knopf = 'h-8 w-8 shrink-0 rounded-[4px] border border-stein-300 bg-white text-stein-700 hover:border-stein-500 disabled:opacity-40'
  return (
    <div className="flex items-center gap-1">
      <button type="button" className={knopf} aria-label={`${label} verringern`} disabled={wert <= min} onClick={() => onAendern(wert - 1)}>−</button>
      <input type="number" inputMode="numeric" min={min} max={max} aria-label={label}
        className={`${eingabe} w-14 px-1 py-1 text-center`} value={wert} onChange={(ev) => onAendern(Number(ev.target.value))} />
      <button type="button" className={knopf} aria-label={`${label} erhöhen`} disabled={wert >= max} onClick={() => onAendern(wert + 1)}>+</button>
    </div>
  )
}

export default function LeistungsTabelle({
  katalog,
  werte,
  onAendern,
}: {
  katalog: KatalogEintrag[]
  werte: Record<string, Leistung>
  onAendern: (id: string, aenderung: Partial<Leistung>) => void
}) {
  const gruppen = useMemo(() => {
    const g: Record<string, KatalogEintrag[]> = {}
    for (const e of katalog) (g[e.kategorie] ??= []).push(e)
    return g
  }, [katalog])

  return (
    <div className="space-y-3">
      {Object.entries(gruppen).map(([kategorie, eintraege]) => {
        const anzahl = eintraege.filter((e) => werte[e.id]?.haben).length
        return (
          <details key={kategorie} open className="group rounded-md border border-stein-200 bg-white">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 font-semibold text-stein-800">
              <span>{kategorie}</span>
              <span className="flex items-center gap-3 text-xs font-normal text-stein-500">
                {anzahl > 0 ? `${anzahl} ausgewählt` : 'nichts ausgewählt'}
                <span className="transition-transform group-open:rotate-180" aria-hidden>▾</span>
              </span>
            </summary>
            <div className="hidden border-t border-stein-200 bg-stein-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-stein-500 md:grid md:grid-cols-[1fr_11rem_8rem_8rem] md:gap-4">
              <span>Leistung</span><span>Richtwert</span><span>Anzahl</span><span>davon vergeben</span>
            </div>
            <ul className="divide-y divide-stein-100 border-t border-stein-200 md:border-t-0">
              {eintraege.map((e) => {
                const l = werte[e.id] ?? LEER
                return (
                  <li key={e.id} className={`grid gap-x-4 gap-y-2 px-4 py-3 md:grid-cols-[1fr_11rem_8rem_8rem] md:items-center ${l.haben ? 'bg-rasen-50/50' : ''}`}>
                    <label className="flex min-w-0 cursor-pointer items-start gap-3">
                      <input type="checkbox" className="mt-1 h-4 w-4 shrink-0 accent-rasen-700" checked={l.haben}
                        onChange={(ev) => onAendern(e.id, { haben: ev.target.checked })} />
                      <span className="min-w-0">
                        <span className={`block text-sm ${l.haben ? 'font-semibold text-stein-900' : 'text-stein-800'}`}>{e.name}</span>
                        <span className="block text-xs text-stein-500">{e.gegenleistung}</span>
                      </span>
                    </label>
                    <span className="pl-7 text-xs text-stein-500 md:pl-0">{richtwertText(e)}</span>
                    {l.haben && (
                      <>
                        <div className="flex items-center justify-between gap-2 pl-7 md:block md:pl-0">
                          <span className="text-xs text-stein-600 md:hidden">Anzahl</span>
                          <Stepper wert={l.anzahl} min={1} max={999} label={`Anzahl ${e.name}`} onAendern={(n) => onAendern(e.id, { anzahl: n })} />
                        </div>
                        <div className="flex items-center justify-between gap-2 pl-7 md:block md:pl-0">
                          <span className="text-xs text-stein-600 md:hidden">davon vergeben</span>
                          <Stepper wert={l.vergeben} min={0} max={l.anzahl} label={`davon vergeben ${e.name}`} onAendern={(n) => onAendern(e.id, { vergeben: n })} />
                        </div>
                      </>
                    )}
                  </li>
                )
              })}
            </ul>
          </details>
        )
      })}
    </div>
  )
}
