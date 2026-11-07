import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, euro, STATUS_TEXT } from '../api'
import type { AnalyseZustand, Finanzierungsplan, Kandidat, KandidatStatus, Potenzial, Verein } from '../api'
import Anzeigetafel from '../components/Anzeigetafel'
import KandidatenKarte from '../components/KandidatenKarte'
import PlanKarte from '../components/PlanKarte'
import { Fehler, Karte, Knopf, Lader, ScoreBadge, eingabe } from '../components/ui'
import Benachrichtigung from '../components/Benachrichtigung'

export default function Analyse({ vereinId, onOeffnen }: { vereinId: number; onOeffnen: (kandidatId: number) => void }) {
  const [verein, setVerein] = useState<Verein | null>(null)
  const [potenzial, setPotenzial] = useState<Potenzial | null>(null)
  const [kandidaten, setKandidaten] = useState<Kandidat[]>([])
  const [zustand, setZustand] = useState<AnalyseZustand | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)
  const [markiert, setMarkiert] = useState<number | null>(null)
  const [nurRecherchiert, setNurRecherchiert] = useState(false)
  const [branche, setBranche] = useState('')
  const [status, setStatus] = useState<'' | KandidatStatus>('')
  const [alleAnnahmen, setAlleAnnahmen] = useState(false)
  const [plan, setPlan] = useState<Finanzierungsplan | null>(null)

  const laden = useCallback(async () => {
    try {
      const [v, p, k, r, f] = await Promise.all([
        api.get<Verein>(`/vereine/${vereinId}`),
        api.get<Potenzial>(`/vereine/${vereinId}/potenzial`),
        api.get<Kandidat[]>(`/vereine/${vereinId}/kandidaten`),
        api.get<AnalyseZustand>(`/vereine/${vereinId}/analyse`),
        api.get<Finanzierungsplan>(`/vereine/${vereinId}/plan`),
      ])
      setVerein(v)
      setPotenzial(p)
      setKandidaten(k)
      setZustand(r)
      setPlan(f)
    } catch (err) {
      setFehler((err as Error).message)
    }
  }, [vereinId])

  async function zielSetzen(ziel: number | null) {
    await api.patch<Verein>(`/vereine/${vereinId}`, { ziel_eur: ziel })
    setPlan(await api.get<Finanzierungsplan>(`/vereine/${vereinId}/plan`))
  }

  useEffect(() => {
    laden()
  }, [laden])

  // Während Suche oder Recherche laufen, füllt sich die Liste nach und nach.
  const laeuft = !!zustand && (zustand.suche_status === 'laeuft' || !zustand.recherche.fertig)
  useEffect(() => {
    if (!laeuft) return
    const t = setInterval(laden, 2500)
    return () => clearInterval(t)
  }, [laeuft, laden])

  async function weitereRecherchieren() {
    await api.post(`/vereine/${vereinId}/recherche?anzahl=10`)
    laden()
  }

  const branchen = useMemo(() => [...new Set(kandidaten.map((k) => k.unternehmen.branche))].sort(), [kandidaten])
  const sichtbar = kandidaten.filter(
    (k) =>
      (!nurRecherchiert || k.recherche_status === 'fertig') &&
      (!branche || k.unternehmen.branche === branche) &&
      (!status || k.status === status),
  )
  const recherche = zustand?.recherche
  const fertigAnzahl = recherche?.status.fertig ?? 0
  const offenAnzahl = (recherche?.status.offen ?? 0) + (recherche?.status.fehler ?? 0)
  const sucht = zustand?.suche_status === 'laeuft' && kandidaten.length === 0

  if (!verein || !potenzial) return fehler ? <Fehler text={fehler} /> : <Lader text="Potenzialanalyse wird geladen …" />

  return (
    <div className="space-y-5">
      {plan && (
        <Anzeigetafel
          verein={verein.name}
          untertitel={[verein.ort, verein.spielklasse].filter(Boolean).join(', ')}
          plan={plan}
          onZiel={zielSetzen}
        />
      )}
      <p className="max-w-prose text-sm text-stein-600">
        {potenzial.bestand_sponsoren} bestehende Sponsoren, {(potenzial.betriebe_im_umkreis ?? 0).toLocaleString('de-DE')} Betriebe
        im Umkreis von {verein.radius_km} km, davon {kandidaten.length} passende Kandidaten und {fertigAnzahl} mit Quellen geprüft.{' '}
        {potenzial.hinweis}
      </p>

      {zustand && (laeuft || zustand.suche_status === 'fehler') && (
        <Benachrichtigung vereinId={vereinId} zustand={zustand} kandidaten={kandidaten.length} onAenderung={setZustand} />
      )}

      {plan && <PlanKarte plan={plan} onOeffnen={onOeffnen} />}

      <div className="grid gap-5 lg:grid-cols-3">
        <Karte titel="Eure Lücken" className="lg:col-span-1">
          {potenzial.luecken.length === 0 ? (
            <p className="text-sm text-stein-500">{sucht ? 'Wird gerade ermittelt …' : 'Noch keine Umkreissuche.'}</p>
          ) : (
            <>
              <p className="mb-3 text-sm text-stein-600">Branchen, aus denen ihr noch keinen Sponsor habt, obwohl es Betriebe in der Nähe gibt:</p>
              <div className="flex flex-wrap gap-2">
                {potenzial.luecken.slice(0, 8).map((l) => (
                  <button
                    key={l.branche}
                    onClick={() => setBranche(branche === l.branche ? '' : l.branche)}
                    className={`rounded-[3px] px-2.5 py-1 text-sm font-medium ${branche === l.branche ? 'bg-rasen-700 text-white' : 'bg-signal-100 text-signal-900 hover:bg-signal-200'}`}
                  >
                    {l.branche} ({l.betriebe})
                  </button>
                ))}
              </div>
            </>
          )}
        </Karte>

        <Karte titel="Freie Pakete und Richtpreise" className="lg:col-span-2">
          <ul className="divide-y divide-stein-100 text-sm">
            {potenzial.freie_pakete.map((p) => (
              <li key={p.katalog_id} className="flex items-baseline justify-between gap-3 py-2">
                <span className="text-stein-800">
                  {p.name}
                  {p.annahme && <span className="block text-xs text-stein-500">{p.annahme}</span>}
                </span>
                <span className="shrink-0 text-right font-medium text-stein-900">
                  {euro(p.min)} bis {euro(p.max)}
                  <span className="block text-xs font-normal text-stein-500">
                    {p.eigener_preis ? 'euer Preis' : p.quelle === 'findasponsor' ? 'Marktwert (findasponsor)' : 'Schätzung'}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          {potenzial.vergebene_pakete.length > 0 && (
            <p className="mt-3 text-xs text-stein-500">Schon vergeben (nicht mitgezählt): {potenzial.vergebene_pakete.map((v) => v.name).join(', ')}</p>
          )}
          <button className="mt-2 text-xs text-rasen-800 underline" onClick={() => setAlleAnnahmen(!alleAnnahmen)}>
            {alleAnnahmen ? 'Annahmen ausblenden' : 'Wie rechnen wir?'}
          </button>
          {alleAnnahmen && (
            <ul className="mt-2 list-disc pl-5 text-xs text-stein-600">
              {potenzial.annahmen.map((a) => <li key={a}>{a}</li>)}
              <li>Je Paket wird das mittlere Band der Katalogspanne gezählt.</li>
            </ul>
          )}
        </Karte>
      </div>

      <Karte
        titel={
          <span className="flex flex-wrap items-center gap-3">
            Kandidaten
            {laeuft && <Lader text={`Recherche läuft … ${fertigAnzahl} fertig`} />}
          </span>
        }
      >
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
          <select className={`${eingabe} sm:w-48`} value={branche} onChange={(e) => setBranche(e.target.value)}>
            <option value="">Alle Branchen</option>
            {branchen.map((b) => <option key={b}>{b}</option>)}
          </select>
          <select className={`${eingabe} sm:w-40`} value={status} onChange={(e) => setStatus(e.target.value as '' | KandidatStatus)}>
            <option value="">Jeder Status</option>
            {Object.entries(STATUS_TEXT).map(([w, t]) => <option key={w} value={w}>{t}</option>)}
          </select>
          <label className="flex items-center gap-2 text-sm text-stein-700">
            <input type="checkbox" className="accent-rasen-700" checked={nurRecherchiert} onChange={(e) => setNurRecherchiert(e.target.checked)} />
            nur geprüfte
          </label>
          <span className="sm:ml-auto">
            <Knopf art="sekundaer" onClick={weitereRecherchieren} disabled={!!laeuft || offenAnzahl === 0}>
              Weitere 10 recherchieren
            </Knopf>
          </span>
        </div>

        <div className="grid gap-4 lg:grid-cols-5">
          <ul className="max-h-[560px] space-y-2 overflow-y-auto pr-1 lg:col-span-2">
            {sichtbar.map((k) => {
              const geprueft = k.recherche_status === 'fertig'
              return (
                <li key={k.id}>
                  <button
                    onClick={() => onOeffnen(k.id)}
                    onMouseEnter={() => setMarkiert(k.id)}
                    onMouseLeave={() => setMarkiert(null)}
                    className={`flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                      markiert === k.id ? 'border-rasen-600 bg-rasen-50/50' : 'border-stein-200 hover:border-stein-300'
                    }`}
                  >
                    <ScoreBadge score={geprueft ? k.score : k.vorfilter_score} vorlaeufig={!geprueft} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-stein-900">{k.unternehmen.name}</span>
                      <span className="block text-xs text-stein-500">
                        {k.unternehmen.branche}, {k.entfernung_km.toLocaleString('de-DE')} km
                        {k.status !== 'neu' && `, ${STATUS_TEXT[k.status]}`}
                      </span>
                      {geprueft && k.gruende[0] && <span className="mt-1 line-clamp-2 block text-xs text-stein-600">{k.gruende[0].text}</span>}
                      {k.recherche_status === 'laeuft' && <span className="mt-1 block text-xs text-rasen-700">wird recherchiert …</span>}
                      {k.recherche_status === 'wartet' && <span className="mt-1 block text-xs text-stein-400">in der Warteschlange</span>}
                      {k.recherche_status === 'fehler' && <span className="mt-1 block text-xs text-red-700">Recherche fehlgeschlagen</span>}
                    </span>
                  </button>
                </li>
              )
            })}
            {sichtbar.length === 0 && <li className="text-sm text-stein-500">Keine Kandidaten für diesen Filter.</li>}
          </ul>
          <div className="h-[360px] lg:col-span-3 lg:h-[560px]">
            {verein.lat != null && verein.lon != null ? (
              <KandidatenKarte
                zentrum={[verein.lat, verein.lon]}
                kandidaten={sichtbar}
                markiert={markiert}
                onMarkieren={setMarkiert}
                onOeffnen={onOeffnen}
              />
            ) : (
              <p className="text-sm text-stein-500">Keine Koordinaten für den Verein.</p>
            )}
          </div>
        </div>
      </Karte>
      <Fehler text={fehler} />
    </div>
  )
}

