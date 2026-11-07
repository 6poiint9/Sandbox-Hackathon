import { useMemo } from 'react'
import type { KatalogEintrag } from '../api'

/** Eine Leistung des Vereins im Onboarding: vorhanden? wie viele? davon vergeben? */
export type Leistung = { haben: boolean; anzahl: number; vergeben: number }
export const LEER: Leistung = { haben: false, anzahl: 1, vergeben: 0 }

/** Nur hier ist eine Stückzahl sinnvoll (mehrere Banden, mehrere Banner). Alles andere gibt es einmal. */
export const MIT_ANZAHL = new Set(['bande', 'banner_halle'])

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
  const knopf = 'h-7 w-7 shrink-0 rounded-[3px] border border-stein-300 bg-white text-stein-700 hover:border-stein-500 disabled:opacity-40'
  return (
    <div className="flex items-center gap-1">
      <button type="button" className={knopf} aria-label={`${label} verringern`} disabled={wert <= min} onClick={() => onAendern(wert - 1)}>−</button>
      <input type="number" inputMode="numeric" min={min} max={max} aria-label={label}
        className="h-7 w-12 rounded-[3px] border border-stein-300 bg-white px-1 text-center text-sm focus:border-rasen-600 focus:outline-none focus:ring-2 focus:ring-rasen-600/20" value={wert} onChange={(ev) => onAendern(Number(ev.target.value))} />
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
    <div className="space-y-6">
      {Object.entries(gruppen).map(([kategorie, eintraege]) => {
        const anzahl = eintraege.filter((e) => werte[e.id]?.haben).length
        return (
          <section key={kategorie}>
            <div className="flex items-baseline justify-between gap-3 border-b border-linie pb-1.5">
              <h3 className="text-xl font-semibold text-tinte">{kategorie}</h3>
              <span className="text-sm text-stein-500">{anzahl > 0 ? `${anzahl} gewählt` : ''}</span>
            </div>
            <ul className="mt-3 grid items-start gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {eintraege.map((e) => {
                const l = werte[e.id] ?? LEER
                return (
                  <li key={e.id} className={`rounded-md border p-3 ${l.haben ? 'border-tafel bg-rasen-50/70' : 'border-linie bg-white hover:border-stein-400'}`}>
                    <label className="flex cursor-pointer items-start gap-3">
                      <input type="checkbox" className="mt-1 h-4 w-4 shrink-0 accent-rasen-700" checked={l.haben}
                        onChange={(ev) => onAendern(e.id, { haben: ev.target.checked })} />
                      <span className="min-w-0">
                        <span className={`block text-[15px] leading-snug ${l.haben ? 'font-semibold text-tinte' : 'text-stein-800'}`}>{e.name}</span>
                        <span className="block text-xs text-stein-500">{richtwertText(e)}</span>
                      </span>
                    </label>
                    {l.haben && !MIT_ANZAHL.has(e.id) && (
                      <label className="mt-2 flex cursor-pointer items-center gap-2 pl-7 text-sm text-stein-700">
                        <input type="checkbox" className="h-3.5 w-3.5 accent-rasen-700" checked={l.vergeben > 0}
                          onChange={(ev) => onAendern(e.id, { anzahl: 1, vergeben: ev.target.checked ? 1 : 0 })} />
                        schon an einen Sponsor vergeben
                      </label>
                    )}
                    {l.haben && MIT_ANZAHL.has(e.id) && (
                      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 pl-7 text-sm text-stein-700">
                        <span className="flex items-center gap-2">
                          Anzahl
                          <Stepper wert={l.anzahl} min={1} max={999} label={`Anzahl ${e.name}`} onAendern={(n) => onAendern(e.id, { anzahl: n })} />
                        </span>
                        <span className="flex items-center gap-2">
                          vergeben
                          <Stepper wert={l.vergeben} min={0} max={l.anzahl} label={`davon vergeben ${e.name}`} onAendern={(n) => onAendern(e.id, { vergeben: n })} />
                        </span>
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
