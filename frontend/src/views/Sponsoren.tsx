import { useEffect, useState } from 'react'
import { api, API_URL, euro, STATUS_TEXT } from '../api'
import type { Kandidat, KandidatStatus, Sponsor } from '../api'
import { Fehler, Karte, Knopf, ScoreBadge } from '../components/ui'

const SPALTEN: KandidatStatus[] = ['kontaktiert', 'termin', 'zusage', 'absage']

export default function Sponsoren({ vereinId, onOeffnen }: { vereinId: number; onOeffnen: (id: number) => void }) {
  const [kandidaten, setKandidaten] = useState<Kandidat[]>([])
  const [sponsoren, setSponsoren] = useState<Sponsor[]>([])
  const [fehler, setFehler] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.get<Kandidat[]>(`/vereine/${vereinId}/kandidaten`), api.get<Sponsor[]>(`/vereine/${vereinId}/sponsoren`)])
      .then(([k, s]) => { setKandidaten(k); setSponsoren(s) })
      .catch((e: Error) => setFehler(e.message))
  }, [vereinId])

  const bereit = kandidaten.filter((k) => k.status === 'neu' && k.recherche_status === 'fertig' && (k.score ?? 0) >= 60)

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Sponsoren</h1>
          <p className="text-slate-600">Wen habt ihr angesprochen, wer ist schon dabei.</p>
        </div>
        <a href={`${API_URL}/vereine/${vereinId}/export`}>
          <Knopf art="sekundaer">Als CSV exportieren</Knopf>
        </a>
      </div>

      <Karte titel={`Bereit zur Ansprache (${bereit.length})`}>
        {bereit.length === 0 ? (
          <p className="text-sm text-slate-500">Noch keine geprüften Kandidaten mit Score ab 60.</p>
        ) : (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {bereit.map((k) => <KandidatKachel key={k.id} k={k} onOeffnen={onOeffnen} />)}
          </div>
        )}
      </Karte>

      <div className="grid gap-4 md:grid-cols-4">
        {SPALTEN.map((s) => {
          const liste = kandidaten.filter((k) => k.status === s)
          return (
            <Karte key={s} titel={`${STATUS_TEXT[s]} (${liste.length})`}>
              <div className="space-y-2">
                {liste.map((k) => <KandidatKachel key={k.id} k={k} onOeffnen={onOeffnen} />)}
                {liste.length === 0 && <p className="text-xs text-slate-400">–</p>}
              </div>
            </Karte>
          )
        })}
      </div>

      <Karte titel={`Bestehende Sponsoren (${sponsoren.length})`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr><th className="py-2 pr-3">Firma</th><th className="py-2 pr-3">Gegenleistung</th><th className="py-2 pr-3">Betrag</th><th className="py-2">Laufzeit bis</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sponsoren.map((s) => (
                <tr key={s.id}>
                  <td className="py-2 pr-3 font-medium text-slate-800">{s.firma}</td>
                  <td className="py-2 pr-3 text-slate-600">{s.gegenleistung_text ?? s.gegenleistung ?? '–'}</td>
                  <td className="py-2 pr-3">{s.betrag_eur ? euro(s.betrag_eur) : '–'}</td>
                  <td className="py-2">{s.laufzeit_bis ? new Date(s.laufzeit_bis).toLocaleDateString('de-DE') : '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Karte>
      <Fehler text={fehler} />
    </div>
  )
}

function KandidatKachel({ k, onOeffnen }: { k: Kandidat; onOeffnen: (id: number) => void }) {
  return (
    <button onClick={() => onOeffnen(k.id)} className="flex min-w-[220px] items-center gap-3 rounded-lg border border-slate-200 p-2 text-left hover:border-teal-600">
      <ScoreBadge score={k.score ?? k.vorfilter_score} vorlaeufig={k.recherche_status !== 'fertig'} />
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium text-slate-900">{k.unternehmen.name}</span>
        <span className="block text-xs text-slate-500">{k.unternehmen.branche} · {k.entfernung_km.toLocaleString('de-DE')} km</span>
      </span>
    </button>
  )
}
