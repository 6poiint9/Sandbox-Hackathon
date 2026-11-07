import { useCallback, useEffect, useState } from 'react'
import { api, datum, euro, herunterladen, SPONSOR_STATUS_TEXT, STATUS_TEXT } from '../api'
import type { Aufgabe, Kandidat, KandidatStatus, Sponsor, SponsorStatus } from '../api'
import Verlauf from '../components/Verlauf'
import { Fehler, Feld, Karte, Knopf, ScoreBadge, eingabe } from '../components/ui'

type Reiter = 'bestand' | 'pipeline' | 'aufgaben'
const SPALTEN: KandidatStatus[] = ['kontaktiert', 'termin', 'zusage', 'absage']

export default function Sponsoren({ vereinId, onOeffnen }: { vereinId: number; onOeffnen: (id: number) => void }) {
  const [reiter, setReiter] = useState<Reiter>('bestand')
  const [kandidaten, setKandidaten] = useState<Kandidat[]>([])
  const [sponsoren, setSponsoren] = useState<Sponsor[]>([])
  const [aufgaben, setAufgaben] = useState<Aufgabe[]>([])
  const [offen, setOffen] = useState<number | null>(null)
  const [suche, setSuche] = useState('')
  const [neu, setNeu] = useState('')
  const [fehler, setFehler] = useState<string | null>(null)
  const [meldung, setMeldung] = useState<string | null>(null)

  const laden = useCallback(() => {
    Promise.all([
      api.get<Kandidat[]>(`/vereine/${vereinId}/kandidaten`),
      api.get<Sponsor[]>(`/vereine/${vereinId}/sponsoren`),
      api.get<Aufgabe[]>(`/vereine/${vereinId}/aufgaben`),
    ])
      .then(([k, s, a]) => { setKandidaten(k); setSponsoren(s); setAufgaben(a) })
      .catch((e: Error) => setFehler(e.message))
  }, [vereinId])

  useEffect(() => { laden() }, [laden])

  async function anlegen(e: React.FormEvent) {
    e.preventDefault()
    if (!neu.trim()) return
    const [s] = await api.post<Sponsor[]>(`/vereine/${vereinId}/sponsoren`, [{ firma: neu.trim() }])
    setNeu('')
    laden()
    setOffen(s.id)
  }

  async function importieren(datei: File | undefined) {
    if (!datei) return
    try {
      const r = await api.upload<{ importiert: Sponsor[]; fehler: string[] }>(`/vereine/${vereinId}/sponsoren/import`, datei)
      setMeldung(`${r.importiert.length} Sponsoren importiert${r.fehler.length ? ` · ${r.fehler.length} Zeilen übersprungen: ${r.fehler.join('; ')}` : ''}`)
      laden()
    } catch (err) {
      setFehler((err as Error).message)
    }
  }

  const aktiv = sponsoren.filter((s) => (s.status ?? 'aktiv') !== 'beendet')
  const summe = aktiv.reduce((n, s) => n + (s.betrag_eur ?? 0), 0)
  const gefiltert = sponsoren.filter((s) => s.firma.toLowerCase().includes(suche.toLowerCase()))
  const bereit = kandidaten.filter((k) => k.status === 'neu' && k.recherche_status === 'fertig' && (k.score ?? 0) >= 60)
  const ueberfaellig = aufgaben.filter((a) => a.ueberfaellig).length

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-stein-900">Sponsoren</h1>
          <p className="text-stein-600">Bestand pflegen, Ansprache verfolgen, nichts vergessen.</p>
        </div>
        <Knopf art="sekundaer" onClick={() => herunterladen(`/vereine/${vereinId}/export`, 'sponsorenkompass_kandidaten.csv').catch((e: Error) => setFehler(e.message))}>Kandidaten als CSV</Knopf>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Zahl wert={String(aktiv.length)} text="aktive Sponsoren" />
        <Zahl wert={euro(summe)} text="pro Saison (erfasst)" />
        <Zahl wert={String(kandidaten.filter((k) => ['kontaktiert', 'termin'].includes(k.status)).length)} text="in Ansprache" />
        <Zahl wert={String(aufgaben.length)} text={ueberfaellig ? `Aufgaben · ${ueberfaellig} überfällig` : 'offene Aufgaben'} warnung={ueberfaellig > 0} />
      </div>

      <div className="flex gap-1 border-b border-stein-200">
        {([['bestand', `Bestand (${sponsoren.length})`], ['pipeline', 'Ansprache'], ['aufgaben', `Aufgaben (${aufgaben.length})`]] as [Reiter, string][]).map(([r, t]) => (
          <button key={r} onClick={() => setReiter(r)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${reiter === r ? 'border-rasen-700 font-medium text-rasen-900' : 'border-transparent text-stein-500 hover:text-stein-800'}`}>
            {t}
          </button>
        ))}
      </div>

      {meldung && <p className="rounded-lg bg-rasen-50 px-3 py-2 text-sm text-rasen-900">{meldung}</p>}
      <Fehler text={fehler} />

      {reiter === 'bestand' && (
        <Karte>
          <div className="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center">
            <input className={`${eingabe} lg:w-56`} placeholder="Suchen …" value={suche} onChange={(e) => setSuche(e.target.value)} />
            <form onSubmit={anlegen} className="flex flex-1 gap-2">
              <input className={eingabe} placeholder="Neuer Sponsor (Firmenname)" value={neu} onChange={(e) => setNeu(e.target.value)} />
              <Knopf type="submit" disabled={!neu.trim()}>Anlegen</Knopf>
            </form>
            <label className="cursor-pointer text-sm text-rasen-800 underline">
              CSV importieren
              <input type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => importieren(e.target.files?.[0])} />
            </label>
          </div>
          <ul className="divide-y divide-stein-100">
            {gefiltert.map((s) => (
              <li key={s.id}>
                <button onClick={() => setOffen(offen === s.id ? null : s.id)} className="flex w-full flex-wrap items-center gap-x-4 gap-y-1 py-3 text-left text-sm hover:bg-stein-50">
                  <span className="min-w-0 flex-1 font-medium text-stein-900">{s.firma}</span>
                  <span className="w-48 truncate text-stein-500">{s.gegenleistung_text ?? '–'}</span>
                  <span className="w-24 text-right">{s.betrag_eur ? euro(s.betrag_eur) : '–'}</span>
                  <span className="w-24 text-stein-500">{datum(s.laufzeit_bis)}</span>
                  <StatusPille status={(s.status ?? 'aktiv') as SponsorStatus} />
                </button>
                {offen === s.id && <SponsorEditor vereinId={vereinId} sponsor={s} onGespeichert={laden} onGeloescht={() => { setOffen(null); laden() }} />}
              </li>
            ))}
            {gefiltert.length === 0 && <li className="py-3 text-sm text-stein-500">Keine Sponsoren gefunden.</li>}
          </ul>
        </Karte>
      )}

      {reiter === 'pipeline' && (
        <>
          <Karte titel={`Bereit zur Ansprache (${bereit.length})`}>
            {bereit.length === 0 ? <p className="text-sm text-stein-500">Noch keine geprüften Kandidaten mit Score ab 60.</p> : (
              <div className="flex gap-2 overflow-x-auto pb-1">{bereit.map((k) => <KandidatKachel key={k.id} k={k} onOeffnen={onOeffnen} />)}</div>
            )}
          </Karte>
          <div className="grid gap-4 md:grid-cols-4">
            {SPALTEN.map((st) => {
              const liste = kandidaten.filter((k) => k.status === st)
              return (
                <Karte key={st} titel={`${STATUS_TEXT[st]} (${liste.length})`}>
                  <div className="space-y-2">
                    {liste.map((k) => <KandidatKachel key={k.id} k={k} onOeffnen={onOeffnen} />)}
                    {liste.length === 0 && <p className="text-xs text-stein-400">–</p>}
                  </div>
                </Karte>
              )
            })}
          </div>
        </>
      )}

      {reiter === 'aufgaben' && (
        <Karte titel="Fällig in den nächsten 14 Tagen und auslaufende Sponsorings">
          <ul className="divide-y divide-stein-100">
            {aufgaben.map((a, i) => (
              <li key={i} className="flex flex-wrap items-center gap-3 py-3 text-sm">
                <span className={`w-24 shrink-0 font-medium ${a.ueberfaellig ? 'text-red-700' : 'text-stein-700'}`}>{datum(a.faellig)}</span>
                <span className="rounded bg-stein-100 px-1.5 py-0.5 text-[11px] text-stein-600">{a.art === 'vertragsende' ? 'Vertragsende' : 'Wiedervorlage'}</span>
                <span className="min-w-0 flex-1"><span className="font-medium text-stein-900">{a.titel}</span> – {a.text}</span>
                <Knopf art="leise" onClick={() => a.kandidat_id ? onOeffnen(a.kandidat_id) : (setReiter('bestand'), setOffen(a.sponsor_id))}>Öffnen</Knopf>
              </li>
            ))}
            {aufgaben.length === 0 && <li className="py-3 text-sm text-stein-500">Nichts fällig. Wiedervorlagen setzt ihr beim Sponsor oder Kandidaten.</li>}
          </ul>
        </Karte>
      )}
    </div>
  )
}

function SponsorEditor({ vereinId, sponsor, onGespeichert, onGeloescht }: { vereinId: number; sponsor: Sponsor; onGespeichert: () => void; onGeloescht: () => void }) {
  const [f, setF] = useState<Sponsor>(sponsor)
  const [status, setStatus] = useState<string | null>(null)
  const [verlauf, setVerlauf] = useState(0)
  const set = <K extends keyof Sponsor>(k: K, v: Sponsor[K]) => setF((alt) => ({ ...alt, [k]: v }))
  const leer = (v: string) => (v.trim() === '' ? null : v)

  async function speichern() {
    const { id, ...daten } = f
    void id
    try {
      await api.patch(`/sponsoren/${sponsor.id}`, { ...daten, betrag_eur: f.betrag_eur ? Number(f.betrag_eur) : null })
      setStatus('Gespeichert ✓')
      setVerlauf((n) => n + 1)
      onGespeichert()
    } catch (e) {
      setStatus((e as Error).message)
    }
  }

  async function loeschen() {
    if (!window.confirm(`${sponsor.firma} wirklich löschen?`)) return
    await api.delete(`/sponsoren/${sponsor.id}`)
    onGeloescht()
  }

  return (
    <div className="mb-3 space-y-4 rounded-lg border border-stein-200 bg-stein-50/60 p-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Feld label="Firma"><input className={eingabe} value={f.firma} onChange={(e) => set('firma', e.target.value)} /></Feld>
        <Feld label="Gegenleistung"><input className={eingabe} value={f.gegenleistung_text ?? ''} onChange={(e) => set('gegenleistung_text', leer(e.target.value))} placeholder="z. B. Bande Hauptplatz" /></Feld>
        <Feld label="Status">
          <select className={eingabe} value={f.status ?? 'aktiv'} onChange={(e) => set('status', e.target.value as SponsorStatus)}>
            {Object.entries(SPONSOR_STATUS_TEXT).map(([w, t]) => <option key={w} value={w}>{t}</option>)}
          </select>
        </Feld>
        <Feld label="Betrag pro Saison (€)"><input className={eingabe} inputMode="numeric" value={f.betrag_eur ?? ''} onChange={(e) => set('betrag_eur', e.target.value ? Number(e.target.value.replace(/\D/g, '')) : null)} /></Feld>
        <Feld label="Laufzeit bis"><input type="date" className={eingabe} value={f.laufzeit_bis ?? ''} onChange={(e) => set('laufzeit_bis', leer(e.target.value))} /></Feld>
        <Feld label="Website"><input className={eingabe} value={f.website ?? ''} onChange={(e) => set('website', leer(e.target.value))} /></Feld>
        <Feld label="Ansprechpartner"><input className={eingabe} value={f.ansprechpartner ?? ''} onChange={(e) => set('ansprechpartner', leer(e.target.value))} /></Feld>
        <Feld label="E-Mail"><input type="email" className={eingabe} value={f.email ?? ''} onChange={(e) => set('email', leer(e.target.value))} /></Feld>
        <Feld label="Telefon"><input className={eingabe} value={f.telefon ?? ''} onChange={(e) => set('telefon', leer(e.target.value))} /></Feld>
        <Feld label="Nächster Schritt"><input className={eingabe} value={f.naechster_schritt ?? ''} onChange={(e) => set('naechster_schritt', leer(e.target.value))} placeholder="z. B. Verlängerung anbieten" /></Feld>
        <Feld label="Wiedervorlage am"><input type="date" className={eingabe} value={f.wiedervorlage ?? ''} onChange={(e) => set('wiedervorlage', leer(e.target.value))} /></Feld>
        <Feld label="Notiz"><input className={eingabe} value={f.notiz ?? ''} onChange={(e) => set('notiz', leer(e.target.value))} /></Feld>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Knopf onClick={speichern}>Speichern</Knopf>
        <Knopf art="leise" onClick={loeschen}>Löschen</Knopf>
        {status && <span className="text-sm text-stein-600">{status}</span>}
      </div>
      <div>
        <p className="mb-2 text-sm font-semibold text-stein-700">Verlauf</p>
        <Verlauf vereinId={vereinId} sponsorId={sponsor.id} neuLaden={verlauf} />
      </div>
    </div>
  )
}

function StatusPille({ status }: { status: SponsorStatus }) {
  const farbe = { aktiv: 'bg-rasen-100 text-rasen-900', verlaengerung: 'bg-signal-100 text-signal-900', beendet: 'bg-stein-100 text-stein-500' }[status]
  return <span className={`w-36 rounded-full px-2 py-0.5 text-center text-xs ${farbe}`}>{SPONSOR_STATUS_TEXT[status]}</span>
}

function Zahl({ wert, text, warnung }: { wert: string; text: string; warnung?: boolean }) {
  return (
    <div className={`rounded-md border bg-white px-4 py-3 ${warnung ? 'border-red-200' : 'border-linie'}`}>
      <p className={`text-xl font-semibold ${warnung ? 'text-red-700' : 'text-stein-900'}`}>{wert}</p>
      <p className="text-xs text-stein-500">{text}</p>
    </div>
  )
}

function KandidatKachel({ k, onOeffnen }: { k: Kandidat; onOeffnen: (id: number) => void }) {
  return (
    <button onClick={() => onOeffnen(k.id)} className="flex min-w-[220px] items-center gap-3 rounded-lg border border-stein-200 p-2 text-left hover:border-rasen-600">
      <ScoreBadge score={k.score ?? k.vorfilter_score} vorlaeufig={k.recherche_status !== 'fertig'} />
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium text-stein-900">{k.unternehmen.name}</span>
        <span className="block text-xs text-stein-500">
          {k.unternehmen.branche}{k.wiedervorlage ? ` · WV ${datum(k.wiedervorlage)}` : ` · ${k.entfernung_km.toLocaleString('de-DE')} km`}
        </span>
      </span>
    </button>
  )
}
