import { euro } from '../api'
import type { Finanzierungsplan } from '../api'
import { Karte } from './ui'

// Wie das Ziel erreicht wird: Pakete aus dem Inventar, je Paket die besten Kandidaten.
export default function PlanKarte({
  plan,
  onOeffnen,
}: {
  plan: Finanzierungsplan
  onOeffnen: (kandidatId: number) => void
}) {
  if (plan.zeilen.length === 0) return null
  return (
    <Karte titel="So erreicht ihr euer Ziel">
      <p className="mb-4 max-w-prose text-[15px] text-stein-600">
        Es fehlen {euro(plan.luecke_eur ?? 0)} pro Saison. Zuerst ein großes Paket als Hauptsponsor, dann Partner,
        bis die Lücke gedeckt ist. Bei jedem Paket stehen die Betriebe, die am besten dazu passen.
      </p>
      <div className="text-[15px]">
        {plan.zeilen.map((z) => (
          <div key={z.katalog_id} className="grid gap-x-4 gap-y-1 border-t border-linie py-3 sm:grid-cols-[1.1fr_1.6fr_auto]">
            <p>
              <span className="font-tafel text-xl font-bold text-rasen-700">{z.anzahl}×</span>{' '}
              <span className="font-semibold">{z.name}</span>
            </p>
            {z.kandidaten.length === 0 ? (
              <p className="text-stein-500">Noch kein passender Betrieb gefunden</p>
            ) : (
              <ul className="space-y-1">
                {z.kandidaten.map((c) => (
                  <li key={c.kandidat_id}>
                    <button
                      onClick={() => onOeffnen(c.kandidat_id)}
                      className={`text-left underline decoration-linie underline-offset-4 hover:decoration-rasen-600 ${c.geprueft ? 'text-tinte' : 'text-stein-500'}`}
                    >
                      {c.name}
                    </button>
                    <span className="ml-2 text-sm text-stein-500">
                      {c.geprueft ? `Score ${c.score ?? '–'}` : 'noch nicht geprüft'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="font-semibold sm:whitespace-nowrap sm:text-right">
              {euro(z.min)} bis {euro(z.max)}
            </p>
          </div>
        ))}
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-t-2 border-tinte py-3">
          <p className="font-semibold">{plan.neue_sponsoren} neue Sponsoren</p>
          <p className="font-tafel text-xl font-bold">
            {euro(plan.summe_min)} bis {euro(plan.summe_max)}
          </p>
        </div>
      </div>
      {plan.hebel.length > 0 && (
        <div className="mt-4 border-l-4 border-signal-400 bg-signal-50 px-4 py-3">
          <p className="font-semibold">Was ihr tun könnt</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-[15px] text-stein-700">
            {plan.hebel.map((h) => <li key={h}>{h}</li>)}
          </ul>
        </div>
      )}
    </Karte>
  )
}
