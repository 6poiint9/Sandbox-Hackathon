import type { ReactNode } from 'react'

export function scoreFarbe(score: number | null | undefined) {
  if (score == null) return 'bg-slate-200 text-slate-600'
  if (score >= 70) return 'bg-teal-700 text-white'
  if (score >= 45) return 'bg-amber-500 text-white'
  return 'bg-slate-400 text-white'
}

export function ScoreBadge({ score, vorlaeufig }: { score: number | null; vorlaeufig?: boolean }) {
  return (
    <span
      title={vorlaeufig ? 'Vorläufig (Vorfilter), noch nicht recherchiert' : 'Bewertung nach Recherche'}
      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
        vorlaeufig ? 'border-2 border-dashed border-slate-300 bg-white text-slate-500' : scoreFarbe(score)
      }`}
    >
      {score ?? '–'}
    </span>
  )
}

export function Karte({ titel, children, className = '' }: { titel?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 ${className}`}>
      {titel && <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{titel}</h2>}
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
  art?: 'primaer' | 'sekundaer' | 'leise'
  disabled?: boolean
  type?: 'button' | 'submit'
}) {
  const stil = {
    primaer: 'bg-teal-700 text-white hover:bg-teal-800 disabled:bg-slate-300',
    sekundaer: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:text-slate-400',
    leise: 'text-teal-800 hover:bg-teal-50 disabled:text-slate-400',
  }[art]
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${stil}`}
    >
      {children}
    </button>
  )
}

export function Fehler({ text }: { text: string | null }) {
  if (!text) return null
  return <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{text}</p>
}

export function Lader({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-600">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-teal-700 border-t-transparent" />
      {text}
    </div>
  )
}

export function Feld({ label, children, hinweis }: { label: string; children: ReactNode; hinweis?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {children}
      {hinweis && <span className="mt-1 block text-xs text-slate-500">{hinweis}</span>}
    </label>
  )
}

export const eingabe =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20'
