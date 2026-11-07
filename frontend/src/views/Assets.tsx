import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, datum, euro } from '../api'
import type { AssetAnsicht, KatalogEintrag, Sponsor } from '../api'
import { Fehler, Feld, Karte, Knopf, eingabe } from '../components/ui'

export default function Assets({ vereinId }: { vereinId: number }) {
  const [assets, setAssets] = useState<AssetAnsicht[]>([])
  const [katalog, setKatalog] = useState<KatalogEintrag[]>([])
  const [sponsoren, setSponsoren] = useState<Sponsor[]>([])
  const [neu, setNeu] = useState('')
  const [offen, setOffen] = useState<number | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)

  const laden = useCallback(() => {
    Promise.all([
      api.get<AssetAnsicht[]>(`/vereine/${vereinId}/assets`),
      api.get<KatalogEintrag[]>('/katalog'),
      api.get<Sponsor[]>(`/vereine/${vereinId}/sponsoren`),
    ])
      .then(([a, k, s]) => { setAssets(a); setKatalog(k); setSponsoren(s) })
      .catch((e: Error) => setFehler(e.message))
  }, [vereinId])

  useEffect(() => { laden() }, [laden])

  async function aktion(f: () => Promise<unknown>) {
    setFehler(null)
    try {
      const r = await f()
      if (Array.isArray(r)) setAssets(r as AssetAnsicht[])
      else laden()
    } catch (e) {
      setFehler((e as Error).message)
    }
  }

  const vorhanden = new Set(assets.map((a) => a.katalog_id))
  const gruppen = useMemo(() => {
    const g: Record<string, AssetAnsicht[]> = {}
    for (const a of assets) (g[a.kategorie] ??= []).push(a)
    return g
  }, [assets])
  const einnahmen = assets.reduce((n, a) => n + a.einnahmen_eur, 0)
  const einheiten = assets.reduce((n, a) => n + a.anzahl, 0)
  const frei = assets.reduce((n, a) => n + a.frei, 0)

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Sponsoring-Assets</h1>
        <p className="text-slate-600">Was ihr anbieten könnt, wie viel davon vergeben ist und an wen.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Zahl wert={String(assets.length)} text="Asset-Arten" />
        <Zahl wert={`${einheiten - frei} / ${einheiten}`} text="Einheiten vergeben" />
        <Zahl wert={String(frei)} text="Einheiten frei" />
        <Zahl wert={euro(einnahmen)} text="vertraglich pro Saison" />
      </div>

      <Karte>
        <div className="flex flex-col gap-2 sm:flex-row">
          <select className={eingabe} value={neu} onChange={(e) => setNeu(e.target.value)}>
            <option value="">Asset aus dem Katalog hinzufügen …</option>
            {katalog.filter((k) => !vorhanden.has(k.id)).map((k) => <option key={k.id} value={k.id}>{k.kategorie} · {k.name}</option>)}
          </select>
          <Knopf disabled={!neu} onClick={() => aktion(async () => { const r = await api.post(`/vereine/${vereinId}/assets`, { katalog_id: neu }); setNeu(''); return r })}>Hinzufügen</Knopf>
        </div>
      </Karte>
      <Fehler text={fehler} />

      {Object.entries(gruppen).map(([kategorie, liste]) => (
        <section key={kategorie}>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">{kategorie}</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {liste.map((a) => (
              <Karte key={a.id}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900">{a.name}</p>
                    <p className="text-xs text-slate-500">{a.beschreibung || a.gegenleistung}</p>
                  </div>
                  <button className="text-xs text-teal-800 underline" onClick={() => setOffen(offen === a.id ? null : a.id)}>
                    {offen === a.id ? 'Schließen' : 'Bearbeiten'}
                  </button>
                </div>
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-slate-600">
                    <span>{a.belegt} von {a.anzahl} vergeben</span>
                    <span>
                      {a.preis_eur ? `${euro(a.preis_eur)} je Einheit` : a.richtpreis ? `Richtwert ${euro(a.richtpreis.min)}–${euro(a.richtpreis.max)}` : 'Sachleistung'}
                    </span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full bg-teal-600" style={{ width: `${(a.belegt / a.anzahl) * 100}%` }} />
                  </div>
                </div>
                {a.vergaben.length > 0 && (
                  <ul className="mt-3 space-y-1 text-sm">
                    {a.vergaben.map((v) => (
                      <li key={v.id} className="flex items-center justify-between gap-2">
                        <span className="min-w-0 truncate">{v.anzahl}× <span className="font-medium">{v.sponsor}</span></span>
                        <span className="shrink-0 text-xs text-slate-500">
                          {v.preis_eur ? euro(v.preis_eur) : ''}{v.bis ? ` · bis ${datum(v.bis)}` : ''}
                          {offen === a.id && <button className="ml-2 text-red-700" onClick={() => aktion(() => api.delete(`/vergaben/${v.id}`))}>×</button>}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                {a.belegt > 0 && a.vergaben.length === 0 && <p className="mt-2 text-xs text-slate-500">Als „schon vergeben“ markiert – Sponsor unten zuordnen.</p>}
                {offen === a.id && <AssetEditor asset={a} sponsoren={sponsoren} aktion={aktion} />}
              </Karte>
            ))}
          </div>
        </section>
      ))}
      {assets.length === 0 && <p className="text-sm text-slate-500">Noch keine Assets. Fügt oben hinzu, was ihr anbieten könnt.</p>}
    </div>
  )
}

function AssetEditor({ asset, sponsoren, aktion }: { asset: AssetAnsicht; sponsoren: Sponsor[]; aktion: (f: () => Promise<unknown>) => void }) {
  const [anzahl, setAnzahl] = useState(String(asset.anzahl))
  const [preis, setPreis] = useState(asset.preis_eur ? String(asset.preis_eur) : '')
  const [beschreibung, setBeschreibung] = useState(asset.beschreibung ?? '')
  const [sponsor, setSponsor] = useState('')
  const [vAnzahl, setVAnzahl] = useState('1')
  const [vPreis, setVPreis] = useState('')
  const [vBis, setVBis] = useState('')
  const zahl = (s: string) => (s ? Number(s.replace(/\D/g, '')) : null)

  return (
    <div className="mt-4 space-y-4 border-t border-slate-100 pt-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Feld label="Anzahl"><input className={eingabe} inputMode="numeric" value={anzahl} onChange={(e) => setAnzahl(e.target.value)} /></Feld>
        <Feld label="Euer Preis je Einheit (€)"><input className={eingabe} inputMode="numeric" value={preis} onChange={(e) => setPreis(e.target.value)} placeholder={asset.richtpreis ? `${asset.richtpreis.min}–${asset.richtpreis.max}` : ''} /></Feld>
        <Feld label="Beschreibung"><input className={eingabe} value={beschreibung} onChange={(e) => setBeschreibung(e.target.value)} placeholder="z. B. 3 × 1 m, Hauptplatz" /></Feld>
      </div>
      <div className="flex flex-wrap gap-2">
        <Knopf art="sekundaer" onClick={() => aktion(() => api.patch(`/assets/${asset.id}`, { anzahl: zahl(anzahl) ?? 1, preis_eur: zahl(preis), beschreibung: beschreibung || null }))}>Speichern</Knopf>
        <Knopf art="leise" onClick={() => window.confirm(`${asset.name} entfernen?`) && aktion(() => api.delete(`/assets/${asset.id}`))}>Asset entfernen</Knopf>
      </div>
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">An Sponsor vergeben</p>
        <div className="grid gap-2 sm:grid-cols-4">
          <select className={`${eingabe} sm:col-span-2`} value={sponsor} onChange={(e) => setSponsor(e.target.value)}>
            <option value="">Sponsor wählen …</option>
            {sponsoren.map((s) => <option key={s.id} value={s.id}>{s.firma}</option>)}
          </select>
          <input className={eingabe} inputMode="numeric" value={vAnzahl} onChange={(e) => setVAnzahl(e.target.value)} placeholder="Anzahl" />
          <input className={eingabe} inputMode="numeric" value={vPreis} onChange={(e) => setVPreis(e.target.value)} placeholder="€ / Saison" />
          <input type="date" className={`${eingabe} sm:col-span-2`} value={vBis} onChange={(e) => setVBis(e.target.value)} />
          <Knopf disabled={!sponsor} onClick={() => aktion(() => api.post(`/assets/${asset.id}/vergaben`, { sponsor_id: Number(sponsor), anzahl: zahl(vAnzahl) ?? 1, preis_eur: zahl(vPreis), bis: vBis || null }))}>Vergeben</Knopf>
        </div>
      </div>
    </div>
  )
}

function Zahl({ wert, text }: { wert: string; text: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <p className="text-xl font-semibold text-slate-900">{wert}</p>
      <p className="text-xs text-slate-500">{text}</p>
    </div>
  )
}
