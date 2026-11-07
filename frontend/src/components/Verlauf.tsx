import { useCallback, useEffect, useState } from 'react'
import { AKTIVITAET_TEXT, api } from '../api'
import type { Aktivitaet, AktivitaetArt } from '../api'
import { Fehler, Knopf, eingabe } from './ui'

const ARTEN: AktivitaetArt[] = ['notiz', 'anruf', 'brief', 'email', 'treffen']

export default function Verlauf({
  vereinId,
  sponsorId,
  kandidatId,
  neuLaden = 0,
}: {
  vereinId: number
  sponsorId?: number
  kandidatId?: number
  neuLaden?: number
}) {
  const [eintraege, setEintraege] = useState<Aktivitaet[]>([])
  const [art, setArt] = useState<AktivitaetArt>('notiz')
  const [text, setText] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)

  const filter = sponsorId != null ? `sponsor_id=${sponsorId}` : `kandidat_id=${kandidatId}`
  const laden = useCallback(() => {
    api.get<Aktivitaet[]>(`/vereine/${vereinId}/aktivitaeten?${filter}`).then(setEintraege).catch((e: Error) => setFehler(e.message))
  }, [vereinId, filter])

  useEffect(() => {
    laden()
  }, [laden, neuLaden])

  async function speichern(e: React.FormEvent) {
    e.preventDefault()
    if (!text.trim()) return
    try {
      await api.post(`/vereine/${vereinId}/aktivitaeten`, { art, text, sponsor_id: sponsorId ?? null, kandidat_id: kandidatId ?? null })
      setText('')
      laden()
    } catch (err) {
      setFehler((err as Error).message)
    }
  }

  return (
    <div>
      <form onSubmit={speichern} className="flex flex-col gap-2 sm:flex-row">
        <select className={`${eingabe} sm:w-32`} value={art} onChange={(e) => setArt(e.target.value as AktivitaetArt)}>
          {ARTEN.map((a) => <option key={a} value={a}>{AKTIVITAET_TEXT[a]}</option>)}
        </select>
        <input className={eingabe} value={text} onChange={(e) => setText(e.target.value)} placeholder="Was ist passiert? z. B. „Mit Inhaber telefoniert, Rückruf Freitag“" />
        <Knopf type="submit" art="sekundaer" disabled={!text.trim()}>Eintragen</Knopf>
      </form>
      <Fehler text={fehler} />
      <ol className="mt-3 space-y-2">
        {eintraege.map((a) => (
          <li key={a.id} className="flex gap-3 text-sm">
            <span className="w-20 shrink-0 text-xs text-slate-500">{new Date(a.zeitpunkt).toLocaleDateString('de-DE')}</span>
            <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600">{AKTIVITAET_TEXT[a.art] ?? a.art}</span>
            <span className="min-w-0 text-slate-700">{a.text}</span>
          </li>
        ))}
        {eintraege.length === 0 && <li className="text-xs text-slate-400">Noch keine Einträge.</li>}
      </ol>
    </div>
  )
}
