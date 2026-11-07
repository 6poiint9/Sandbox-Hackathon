import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, datum, euro } from '../api'
import type { AssetAnsicht, KatalogEintrag, Sponsor } from '../api'
import { Stepper } from '../components/LeistungsTabelle'
import { Fehler, Knopf, eingabe } from '../components/ui'

/** Sponsoring-Angebot des Vereins: welche Leistungen es gibt, wie viele, was vergeben ist und an wen. */
export default function Angebot({ vereinId }: { vereinId: number }) {
  const [leistungen, setLeistungen] = useState<AssetAnsicht[]>([])
  const [katalog, setKatalog] = useState<KatalogEintrag[]>([])
  const [sponsoren, setSponsoren] = useState<Sponsor[]>([])
  const [neu, setNeu] = useState('')
  const [offen, setOffen] = useState<number | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)

  const laden = useCallback(() => {
    setFehler(null)
    Promise.all([
      api.get<AssetAnsicht[]>(`/vereine/${vereinId}/assets`),
      api.get<KatalogEintrag[]>('/katalog'),
      api.get<Sponsor[]>(`/vereine/${vereinId}/sponsoren`),
    ])
      .then(([a, k, s]) => { setLeistungen(a); setKatalog(k); setSponsoren(s) })
      .catch((e: Error) => setFehler(e.message))
  }, [vereinId])

  useEffect(() => { laden() }, [laden])

  async function aktion(f: () => Promise<unknown>) {
    setFehler(null)
    try {
      const r = await f()
      if (Array.isArray(r)) setLeistungen(r as AssetAnsicht[])
      else laden()
    } catch (e) {
      setFehler((e as Error).message)
    }
  }

  const gruppen = useMemo(() => {
    const g: Record<string, AssetAnsicht[]> = {}
    for (const a of leistungen) (g[a.kategorie] ??= []).push(a)
    return g
  }, [leistungen])
  const vorhanden = new Set(leistungen.map((a) => a.katalog_id))
  const einheiten = leistungen.reduce((n, a) => n + a.anzahl, 0)
  const frei = leistungen.reduce((n, a) => n + a.frei, 0)
  const einnahmen = leistungen.reduce((n, a) => n + a.einnahmen_eur, 0)

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-3xl font-semibold text-tinte">Sponsoring-Angebot</h1>
        <p className="text-stein-600">Was ihr Sponsoren bieten könnt, wie viel davon vergeben ist und an wen.</p>
      </div>

      <p className="max-w-prose text-[15px] text-stein-700">
        {leistungen.length} Leistungen mit {einheiten} Einheiten, davon {einheiten - frei} vergeben und{' '}
        <strong className={frei > 0 ? 'text-rasen-700' : ''}>{frei} frei</strong>. Vertraglich gesichert: {euro(einnahmen)} pro Saison.
      </p>
      <Fehler text={fehler} />

      {Object.entries(gruppen).map(([kategorie, liste]) => (
        <section key={kategorie} className="overflow-hidden rounded-md border border-linie bg-white">
          <h2 className="border-b border-linie px-4 py-3 text-xl font-semibold text-tinte">{kategorie}</h2>
          <div className="hidden bg-stein-50 px-4 py-2 text-xs font-semibold text-stein-600 md:grid md:grid-cols-[1fr_8rem_9rem_9rem_2rem] md:gap-4">
            <span>Leistung</span><span>Anzahl</span><span>Belegung</span><span>Preis je Einheit</span><span />
          </div>
          <ul className="divide-y divide-stein-100">
            {liste.map((a) => (
              <li key={a.id}>
                <div className="grid gap-x-4 gap-y-2 px-4 py-3 md:grid-cols-[1fr_8rem_9rem_9rem_2rem] md:items-center">
                  <button className="min-w-0 text-left" onClick={() => setOffen(offen === a.id ? null : a.id)}>
                    <span className="block text-sm font-semibold text-stein-900">{a.name}</span>
                    <span className="block text-xs text-stein-500">
                      {a.vergaben.length > 0 ? a.vergaben.map((v) => v.sponsor).join(', ') : a.beschreibung || a.gegenleistung}
                    </span>
                  </button>
                  <Zelle label="Anzahl">
                    <Stepper wert={a.anzahl} min={Math.max(1, a.belegt)} max={999} label={`Anzahl ${a.name}`}
                      onAendern={(n) => aktion(() => api.patch(`/assets/${a.id}`, { anzahl: Math.max(1, n) }))} />
                  </Zelle>
                  <Zelle label="Belegung">
                    <div className="w-full">
                      <div className="flex justify-between text-xs text-stein-600">
                        <span>{a.belegt} vergeben</span>
                        <span className={a.frei > 0 ? 'font-semibold text-rasen-800' : ''}>{a.frei} frei</span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden bg-stein-100">
                        <div className="h-full bg-rasen-600" style={{ width: `${(a.belegt / a.anzahl) * 100}%` }} />
                      </div>
                    </div>
                  </Zelle>
                  <Zelle label="Preis je Einheit">
                    <PreisFeld asset={a} onSpeichern={(preis) => aktion(() => api.patch(`/assets/${a.id}`, { preis_eur: preis }))} />
                  </Zelle>
                  <button className="hidden text-stein-500 hover:text-stein-900 md:block" aria-label="Details" onClick={() => setOffen(offen === a.id ? null : a.id)}>
                    <span className={`inline-block transition-transform ${offen === a.id ? 'rotate-180' : ''}`}>▾</span>
                  </button>
                </div>
                {offen === a.id && <Details asset={a} sponsoren={sponsoren} aktion={aktion} />}
              </li>
            ))}
          </ul>
        </section>
      ))}

      {leistungen.length === 0 && <p className="text-sm text-stein-500">Noch keine Leistungen. Fügt unten hinzu, was ihr anbieten könnt.</p>}

      <div className="flex flex-col gap-2 rounded-md border border-dashed border-stein-300 bg-white p-4 sm:flex-row">
        <select className={eingabe} value={neu} onChange={(e) => setNeu(e.target.value)}>
          <option value="">Weitere Leistung hinzufügen …</option>
          {katalog.filter((k) => !vorhanden.has(k.id)).map((k) => <option key={k.id} value={k.id}>{k.kategorie}: {k.name}</option>)}
        </select>
        <Knopf disabled={!neu} onClick={() => aktion(async () => { const r = await api.post(`/vereine/${vereinId}/assets`, { katalog_id: neu }); setNeu(''); return r })}>Hinzufügen</Knopf>
      </div>
    </div>
  )
}

function Zelle({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 md:block">
      <span className="text-xs text-stein-500 md:hidden">{label}</span>
      {children}
    </div>
  )
}

function PreisFeld({ asset, onSpeichern }: { asset: AssetAnsicht; onSpeichern: (preis: number | null) => void }) {
  const [wert, setWert] = useState(asset.preis_eur ? String(asset.preis_eur) : '')
  useEffect(() => setWert(asset.preis_eur ? String(asset.preis_eur) : ''), [asset.preis_eur])
  const platzhalter = asset.richtpreis ? `${asset.richtpreis.min}–${asset.richtpreis.max}` : 'Sachleistung'
  function speichern() {
    const zahl = wert ? Number(wert.replace(/\D/g, '')) : null
    if (zahl !== (asset.preis_eur ?? null)) onSpeichern(zahl)
  }
  return (
    <div className="flex items-center gap-1">
      <input className={`${eingabe} w-28 py-1.5 text-right`} inputMode="numeric" value={wert} placeholder={platzhalter}
        aria-label={`Preis je Einheit ${asset.name}`} onChange={(e) => setWert(e.target.value)} onBlur={speichern}
        onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()} />
      <span className="text-xs text-stein-500">€</span>
    </div>
  )
}

function Details({ asset, sponsoren, aktion }: { asset: AssetAnsicht; sponsoren: Sponsor[]; aktion: (f: () => Promise<unknown>) => void }) {
  const [sponsor, setSponsor] = useState('')
  const [anzahl, setAnzahl] = useState(1)
  const [preis, setPreis] = useState('')
  const [bis, setBis] = useState('')
  const [beschreibung, setBeschreibung] = useState(asset.beschreibung ?? '')
  const zugeordnet = asset.vergaben.reduce((n, v) => n + v.anzahl, 0)
  const ohneZuordnung = asset.belegt_manuell

  return (
    <div className="space-y-4 border-t border-stein-100 bg-stein-50/60 px-4 py-4 text-sm">
      <div>
        <p className="mb-2 font-semibold text-stein-800">Vergeben an</p>
        {asset.vergaben.length === 0 && ohneZuordnung === 0 && <p className="text-stein-500">Noch nichts vergeben.</p>}
        <ul className="space-y-1">
          {asset.vergaben.map((v) => (
            <li key={v.id} className="flex flex-wrap items-center justify-between gap-2 rounded-[4px] bg-white px-3 py-2">
              <span><strong>{v.anzahl}×</strong> {v.sponsor}</span>
              <span className="flex items-center gap-3 text-xs text-stein-500">
                {v.preis_eur ? euro(v.preis_eur) : 'ohne Betrag'}{v.bis ? `, bis ${datum(v.bis)}` : ''}
                <button className="text-red-700 hover:underline" onClick={() => aktion(() => api.delete(`/vergaben/${v.id}`))}>entfernen</button>
              </span>
            </li>
          ))}
        </ul>
        {(ohneZuordnung > 0 || asset.vergaben.length > 0) && (
          <div className="mt-2 flex flex-wrap items-center gap-3 text-stein-600">
            <span>Ohne Sponsor-Zuordnung vergeben:</span>
            <Stepper wert={ohneZuordnung} min={0} max={asset.anzahl - zugeordnet} label="ohne Zuordnung vergeben"
              onAendern={(n) => aktion(() => api.patch(`/assets/${asset.id}`, { belegt_manuell: Math.max(0, n) }))} />
          </div>
        )}
      </div>

      {asset.frei > 0 ? (
        <div>
          <p className="mb-2 font-semibold text-stein-800">Einem Sponsor zuordnen</p>
          <div className="grid gap-2 md:grid-cols-[1fr_auto_8rem_10rem_auto] md:items-center">
            <select className={eingabe} value={sponsor} onChange={(e) => setSponsor(e.target.value)}>
              <option value="">Sponsor wählen …</option>
              {sponsoren.map((s) => <option key={s.id} value={s.id}>{s.firma}</option>)}
            </select>
            <Stepper wert={anzahl} min={1} max={asset.frei} label="Anzahl" onAendern={(n) => setAnzahl(Math.max(1, Math.min(asset.frei, n || 1)))} />
            <input className={eingabe} inputMode="numeric" placeholder="€ / Saison" value={preis} onChange={(e) => setPreis(e.target.value)} />
            <input type="date" className={eingabe} aria-label="Laufzeit bis" value={bis} onChange={(e) => setBis(e.target.value)} />
            <Knopf disabled={!sponsor} onClick={() => aktion(async () => {
              const r = await api.post(`/assets/${asset.id}/vergaben`, { sponsor_id: Number(sponsor), anzahl, preis_eur: preis ? Number(preis.replace(/\D/g, '')) : null, bis: bis || null })
              setSponsor(''); setAnzahl(1); setPreis(''); setBis('')
              return r
            })}>Zuordnen</Knopf>
          </div>
        </div>
      ) : (
        <p className="text-stein-600">Alle Einheiten sind vergeben. Anzahl erhöhen, um mehr anzubieten.</p>
      )}

      <div className="flex flex-col gap-2 md:flex-row md:items-center">
        <input className={eingabe} value={beschreibung} onChange={(e) => setBeschreibung(e.target.value)} placeholder="Beschreibung, z. B. 3 × 1 m, Hauptplatz" />
        <Knopf art="sekundaer" onClick={() => aktion(() => api.patch(`/assets/${asset.id}`, { beschreibung: beschreibung || null }))}>Beschreibung speichern</Knopf>
        <Knopf art="leise" onClick={() => window.confirm(`${asset.name} aus dem Angebot entfernen?`) && aktion(() => api.delete(`/assets/${asset.id}`))}>Leistung entfernen</Knopf>
      </div>
    </div>
  )
}

