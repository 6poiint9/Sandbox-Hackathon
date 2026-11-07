import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import type { Finanzierungsplan } from '../api'

// Die Tafel ist das eine auffällige Element der App: Klappziffern wie auf dem Sportplatz.
// Sie klappen beim Laden einmal um und erneut, wenn sich ein Wert ändert (z. B. das Ziel).

const STATUS_TEXT: Record<Finanzierungsplan['status'], (n: number) => string> = {
  ohne_ziel: () => 'Tragt euer Ziel ein, dann rechnen wir aus, wie viele Sponsoren ihr braucht.',
  erreicht: () => 'Euer Ziel ist mit den bestehenden Sponsoren schon erreicht.',
  erreichbar: (n) => `Ziel erreichbar mit ${n} ${n === 1 ? 'neuem Sponsor' : 'neuen Sponsoren'}.`,
  knapp: (n) => `Knapp: mit ${n} ${n === 1 ? 'neuem Sponsor' : 'neuen Sponsoren'} erreichbar, wenn die Preise eher oben liegen.`,
  ueber_potenzial: () => 'Euer Ziel liegt über dem, was eure freien Pakete heute bringen.',
}

function Ziffern({ wert, verzoegerung = 0 }: { wert: number; verzoegerung?: number }) {
  const text = wert.toLocaleString('de-DE')
  return (
    <span className="inline-flex items-stretch gap-[3px]" aria-hidden="true">
      {[...text].map((zeichen, i) =>
        zeichen === '.' ? (
          <span key={i} className="self-end pb-1 font-tafel text-2xl text-signal-400/80 sm:text-3xl">.</span>
        ) : (
          <span
            key={`${text}-${i}`}
            className="klappziffer relative inline-flex w-[0.68em] justify-center rounded-[3px] bg-rasen-950 py-[0.08em] font-tafel font-bold leading-none text-signal-400 shadow-[inset_0_-2px_0_rgba(0,0,0,0.35)]"
            style={{ animationDelay: `${verzoegerung + i * 70}ms` }}
          >
            {zeichen}
            {/* Klappkante */}
            <span className="pointer-events-none absolute inset-x-0 top-1/2 h-px bg-black/45" />
          </span>
        ),
      )}
    </span>
  )
}

function Feld({ titel, children, beschreibung }: { titel: string; children: ReactNode; beschreibung: ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="font-tafel text-lg font-semibold text-kreide/75">{titel}</p>
      <div className="mt-1 text-[2.1rem] sm:text-[2.6rem] lg:text-[3.1rem]">{children}</div>
      <p className="mt-2 text-sm text-kreide/60">{beschreibung}</p>
    </div>
  )
}

export default function Anzeigetafel({
  verein,
  untertitel,
  plan,
  onZiel,
}: {
  verein: string
  untertitel: string
  plan: Finanzierungsplan
  onZiel: (ziel: number | null) => Promise<void>
}) {
  const [bearbeiten, setBearbeiten] = useState(false)
  const [eingabe, setEingabe] = useState(plan.ziel_eur ? String(plan.ziel_eur) : '')
  const [speichert, setSpeichert] = useState(false)

  async function speichern(e: FormEvent) {
    e.preventDefault()
    const zahl = Number(eingabe.replace(/[^\d]/g, ''))
    setSpeichert(true)
    try {
      await onZiel(zahl > 0 ? zahl : null)
      setBearbeiten(false)
    } finally {
      setSpeichert(false)
    }
  }

  const ausgabe = `Bestand ${plan.bestand_eur} Euro, Ziel ${plan.ziel_eur ?? 'offen'}, möglich ${plan.potenzial_min} bis ${plan.potenzial_max} Euro pro Saison.`

  return (
    <section className="rounded-md bg-tafel px-5 pb-5 pt-4 text-kreide sm:px-8 sm:pb-7 sm:pt-6" aria-label="Anzeigetafel">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-kreide/15 pb-3">
        <h1 className="text-3xl font-bold text-white sm:text-4xl">{verein}</h1>
        <p className="font-tafel text-lg text-kreide/70">{untertitel}</p>
      </div>
      <p className="sr-only">{ausgabe}</p>

      <div className="mt-5 grid gap-6 sm:grid-cols-[1fr_1fr_1.7fr] sm:gap-8">
        <Feld titel="Bestand" beschreibung="pro Saison von euren Sponsoren">
          <Ziffern wert={plan.bestand_eur} />
        </Feld>

        <Feld
          titel="Ziel"
          beschreibung={
            bearbeiten ? 'inklusive bestehender Sponsoren' : (
              <>
                euer Ziel pro Saison,{' '}
                <button onClick={() => setBearbeiten(true)} className="underline underline-offset-4 hover:text-kreide">
                  ändern
                </button>
              </>
            )
          }
        >
          {bearbeiten ? (
            <form onSubmit={speichern} className="flex items-center gap-2 text-base">
              <label className="sr-only" htmlFor="ziel">Ziel in Euro pro Saison</label>
              <input
                id="ziel"
                autoFocus
                inputMode="numeric"
                value={eingabe}
                onChange={(e) => setEingabe(e.target.value)}
                placeholder="z. B. 10000"
                className="w-32 rounded-[3px] border border-kreide/30 bg-rasen-950 px-2 py-1.5 font-tafel text-2xl text-signal-400 placeholder:text-kreide/30 focus:outline-none focus:ring-2 focus:ring-signal-400"
              />
              <button type="submit" disabled={speichert} className="rounded-[3px] bg-signal-400 px-3 py-2 text-sm font-semibold text-tinte hover:bg-signal-300">
                {speichert ? 'Rechnet …' : 'Übernehmen'}
              </button>
            </form>
          ) : (
            <button
              onClick={() => setBearbeiten(true)}
              className="text-left"
              title="Ziel ändern"
            >
              {plan.ziel_eur ? (
                <Ziffern wert={plan.ziel_eur} verzoegerung={200} />
              ) : (
                <span className="inline-block rounded-[3px] border border-dashed border-signal-400/70 px-3 py-1 font-tafel text-2xl text-signal-400">
                  Ziel eintragen
                </span>
              )}
            </button>
          )}
        </Feld>

        <Feld titel="Möglich" beschreibung="realistisch für euren Verein, Richtwert">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Ziffern wert={plan.potenzial_min} verzoegerung={400} />
            <span className="font-tafel text-xl text-kreide/60 sm:text-2xl">bis</span>
            <Ziffern wert={plan.potenzial_max} verzoegerung={600} />
          </span>
        </Feld>
      </div>

      <p className="mt-6 border-t border-kreide/15 pt-3 font-tafel text-xl font-semibold text-white sm:text-2xl" aria-live="polite">
        {STATUS_TEXT[plan.status](plan.neue_sponsoren)}
      </p>
    </section>
  )
}
