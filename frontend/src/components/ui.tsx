import type { ReactNode } from 'react'

export function scoreFarbe(score: number | null | undefined) {
  if (score == null) return 'bg-stein-200 text-stein-600'
  if (score >= 70) return 'bg-rasen-600 text-white'
  if (score >= 45) return 'bg-signal-400 text-tinte'
  return 'bg-stein-200 text-stein-700'
}

/** Score als Nummernschild wie auf der Anzeigetafel; gestrichelt = nur Vorfilter. */
export function ScoreBadge({ score, vorlaeufig }: { score: number | null; vorlaeufig?: boolean }) {
  return (
    <span
      title={vorlaeufig ? 'Vorläufig (Vorfilter), noch nicht recherchiert' : 'Bewertung nach Recherche'}
      className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-[3px] font-tafel text-xl font-bold ${
        vorlaeufig ? 'border border-dashed border-stein-400 bg-white text-stein-500' : scoreFarbe(score)
      }`}
    >
      {score ?? '–'}
    </span>
  )
}

/** Ein Aushang: weißes Blatt mit Kreidelinie, ohne Schatten. */
export function Karte({ titel, children, className = '' }: { titel?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-md border border-linie bg-white p-4 sm:p-6 ${className}`}>
      {titel && <h2 className="mb-4 text-2xl font-semibold leading-tight text-tinte">{titel}</h2>}
      {children}
    </section>
  )
}

export function Knopf({
  children,
  onClick,
  art = 'primaer',
  disabled,
  type = 'button',
}: {
  children: ReactNode
  onClick?: () => void
  art?: 'primaer' | 'signal' | 'sekundaer' | 'leise'
  disabled?: boolean
  type?: 'button' | 'submit'
}) {
  const stil = {
    primaer: 'bg-tafel text-white hover:bg-rasen-800 disabled:bg-stein-300',
    signal: 'bg-signal-400 text-tinte hover:bg-signal-300 disabled:bg-stein-200 disabled:text-stein-500',
    sekundaer: 'border border-stein-300 bg-white text-tinte hover:border-stein-500 disabled:text-stein-400',
    leise: 'text-rasen-700 underline-offset-4 hover:underline disabled:text-stein-400',
  }[art]
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-[4px] px-4 py-2 text-[15px] font-semibold transition-colors disabled:cursor-not-allowed ${stil}`}
    >
      {children}
    </button>
  )
}

export function Fehler({ text }: { text: string | null }) {
  if (!text) return null
  return <p className="border-l-4 border-red-700 bg-red-50 px-3 py-2 text-sm text-red-900">{text}</p>
}

export function Lader({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-stein-600">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-rasen-600 border-t-transparent motion-reduce:animate-none" />
      {text}
    </div>
  )
}

export function Feld({ label, children, hinweis }: { label: string; children: ReactNode; hinweis?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-semibold text-stein-800">{label}</span>
      {children}
      {hinweis && <span className="mt-1 block text-xs text-stein-500">{hinweis}</span>}
    </label>
  )
}

export const eingabe =
  'w-full rounded-[4px] border border-stein-300 bg-white px-3 py-2 text-[15px] focus:border-rasen-600 focus:outline-none focus:ring-2 focus:ring-rasen-600/20'
