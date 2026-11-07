import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import type { ErkannterSponsor, KatalogEintrag, ProfilVorschlag, Verein } from '../api'
import { Fehler, Feld, Karte, Knopf, Lader, eingabe } from '../components/ui'

const STANDARD_VORHANDEN = ['bande', 'website', 'social_media', 'spieltag', 'vereinsfest', 'trainingsanzug', 'turnier']
const RECHERCHE_ANZAHL = 10

type InventarWahl = Record<string, 'nein' | 'frei' | 'vergeben'>

export default function Onboarding({ onFertig }: { onFertig: (vereinId: number) => void }) {
  const [website, setWebsite] = useState('')
  const [ort, setOrt] = useState('')
  const [laedt, setLaedt] = useState<string | null>(null)
  const [fehler, setFehler] = useState<string | null>(null)
  const [vorschlag, setVorschlag] = useState<ProfilVorschlag | null>(null)
  const [katalog, setKatalog] = useState<KatalogEintrag[]>([])

  // Formularfelder (vorbefüllt aus der Analyse)
  const [name, setName] = useState('')
  const [spielklasse, setSpielklasse] = useState('')
  const [mitglieder, setMitglieder] = useState('')
  const [zuschauer, setZuschauer] = useState('')
  const [radius, setRadius] = useState('10')
  const [sportstaette, setSportstaette] = useState('')
  const [sponsoren, setSponsoren] = useState<ErkannterSponsor[]>([])
  const [neuerSponsor, setNeuerSponsor] = useState('')
  const [csv, setCsv] = useState<File | null>(null)
  const [inventar, setInventar] = useState<InventarWahl>({})

  useEffect(() => {
    api.get<KatalogEintrag[]>('/katalog').then(setKatalog).catch(() => setFehler('Katalog nicht ladbar – läuft das Backend?'))
  }, [])

  const kategorien = useMemo(() => {
    const gruppen: Record<string, KatalogEintrag[]> = {}
    for (const e of katalog) (gruppen[e.kategorie] ??= []).push(e)
    return gruppen
  }, [katalog])

  async function analysieren(e: React.FormEvent) {
    e.preventDefault()
    setFehler(null)
    setLaedt('Wir lesen eure Website: Mannschaften, Spielklassen, Sportstätte und Sponsoren – auch die Logos. Das dauert etwa eine Minute …')
    try {
      const v = await api.post<ProfilVorschlag>('/onboarding/analyse', { website, ort })
      setVorschlag(v)
      setName(v.name ?? '')
      setOrt(v.ort || ort)
      setSportstaette(v.sportstaette ?? '')
      setSpielklasse(v.spielklasse ?? '')
      setMitglieder(v.mitglieder ? String(v.mitglieder) : '')
      setSponsoren(v.sponsoren)
      const wahl: InventarWahl = {}
      for (const id of STANDARD_VORHANDEN) wahl[id] = 'frei'
      for (const id of v.inventar_vergeben) wahl[id] = 'vergeben'
      setInventar(wahl)
    } catch (err) {
      setFehler(`Analyse fehlgeschlagen: ${(err as Error).message}`)
    } finally {
      setLaedt(null)
    }
  }

  function inventarSetzen(id: string, wert: 'nein' | 'frei' | 'vergeben') {
    setInventar((alt) => ({ ...alt, [id]: wert }))
  }

  async function potenzialBerechnen() {
    if (!vorschlag) return
    setFehler(null)
    try {
      setLaedt('Verein wird angelegt …')
      const verein = await api.post<Verein>('/vereine', {
        name: name || vorschlag.name || 'Unser Verein',
        website: vorschlag.website,
        ort: ort || vorschlag.ort,
        sportstaette: sportstaette || null,
        // Koordinaten nur übernehmen, wenn die Sportstätte unverändert ist – sonst neu verorten
        lat: sportstaette === (vorschlag.sportstaette ?? '') ? vorschlag.lat : null,
        lon: sportstaette === (vorschlag.sportstaette ?? '') ? vorschlag.lon : null,
        sportarten: vorschlag.sportarten,
        mannschaften: vorschlag.mannschaften,
        spielklasse: spielklasse || null,
        mitglieder: mitglieder ? Number(mitglieder) : null,
        zuschauer_schnitt: zuschauer ? Number(zuschauer) : null,
        veranstaltungen: vorschlag.veranstaltungen,
        radius_km: Number(radius) || 10,
      })
      const vid = verein.id
      if (sponsoren.length) {
        await api.post(`/vereine/${vid}/sponsoren`, sponsoren.map(({ firma, website, gegenleistung, gegenleistung_text }) => ({ firma, website, gegenleistung, gegenleistung_text: gegenleistung_text ?? null })))
      }
      if (csv) {
        setLaedt('Sponsorenliste wird importiert …')
        await api.upload(`/vereine/${vid}/sponsoren/import`, csv)
      }
      await api.put(
        `/vereine/${vid}/inventar`,
        Object.entries(inventar)
          .filter(([, w]) => w !== 'nein')
          .map(([katalog_id, w]) => ({ katalog_id, verfuegbar: w === 'frei' })),
      )
      setLaedt('Betriebe im Umkreis werden gesucht (bei einem neuen Ort kann das einige Minuten dauern) …')
      await api.post(`/vereine/${vid}/kandidaten?anzahl=30`)
      await api.post(`/vereine/${vid}/recherche?anzahl=${RECHERCHE_ANZAHL}`)
      onFertig(vid)
    } catch (err) {
      setFehler(`Das hat nicht geklappt: ${(err as Error).message}`)
      setLaedt(null)
    }
  }

  if (!vorschlag) {
    return (
      <div className="mx-auto max-w-xl">
        <h1 className="text-2xl font-semibold text-slate-900 sm:text-3xl">Wie viel Sponsoring steckt in eurem Verein?</h1>
        <p className="mt-2 text-slate-600">
          Nur eure Website eingeben – wir lesen euer Profil und eure Sponsoren aus, finden passende Betriebe rund um eure Sportstätte und zeigen, mit welchem Angebot ihr sie ansprecht.
        </p>
        <Karte className="mt-6">
          <form onSubmit={analysieren} className="space-y-4">
            <Feld label="Website des Vereins">
              <input className={eingabe} value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="z. B. fcemmendingen.de" required />
            </Feld>
            <Feld label="Ort (optional)" hinweis="Nur nötig, wenn die Website keine Adresse der Sportstätte nennt.">
              <input className={eingabe} value={ort} onChange={(e) => setOrt(e.target.value)} placeholder="z. B. Emmendingen" />
            </Feld>
            <Knopf type="submit" disabled={!!laedt}>Potenzial analysieren</Knopf>
            {laedt && <Lader text={laedt} />}
            <Fehler text={fehler} />
          </form>
        </Karte>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Stimmt das so?</h1>
        <p className="mt-1 text-slate-600">Wir haben eure Website ausgelesen. Bitte kurz prüfen und ergänzen – leere Felder haben wir nicht gefunden.</p>
      </div>

      {vorschlag.hinweise.length > 0 && (
        <ul className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          {vorschlag.hinweise.map((h) => <li key={h}>{h}</li>)}
        </ul>
      )}

      <Karte titel="Verein">
        <div className="grid gap-4 sm:grid-cols-2">
          <Feld label="Name"><input className={eingabe} value={name} onChange={(e) => setName(e.target.value)} /></Feld>
          <Feld label="Spielklasse (höchste Mannschaft)"><input className={eingabe} value={spielklasse} onChange={(e) => setSpielklasse(e.target.value)} /></Feld>
          <Feld label="Mitglieder"><input className={eingabe} inputMode="numeric" value={mitglieder} onChange={(e) => setMitglieder(e.target.value.replace(/\D/g, ''))} /></Feld>
          <Feld label="Zuschauer je Heimspiel" hinweis="Schätzung reicht – beeinflusst die Richtpreise.">
            <input className={eingabe} inputMode="numeric" value={zuschauer} onChange={(e) => setZuschauer(e.target.value.replace(/\D/g, ''))} />
          </Feld>
          <Feld label="Suchradius in km"><input className={eingabe} inputMode="numeric" value={radius} onChange={(e) => setRadius(e.target.value.replace(/\D/g, ''))} /></Feld>
          <Feld label="Sportstätte (Mittelpunkt der Suche)" hinweis="Aus der Website, nicht aus dem Impressum. Bitte prüfen.">
            <input className={eingabe} value={sportstaette} onChange={(e) => setSportstaette(e.target.value)} placeholder="z. B. Elzstadion, Emmendingen" />
          </Feld>
          <Feld label="Ort"><input className={eingabe} value={ort} onChange={(e) => setOrt(e.target.value)} /></Feld>
        </div>
        {vorschlag.mannschaften.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-sm font-medium text-slate-700">Mannschaften</p>
            <div className="flex flex-wrap gap-2">
              {vorschlag.mannschaften.map((m) => (
                <span key={m.name} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">
                  {m.name}{m.spielklasse ? ` · ${m.spielklasse}` : ''}
                </span>
              ))}
            </div>
          </div>
        )}
        {vorschlag.veranstaltungen.length > 0 && (
          <p className="mt-3 text-sm text-slate-600">Veranstaltungen: {vorschlag.veranstaltungen.join(', ')}</p>
        )}
      </Karte>

      <Karte titel={`Bestehende Sponsoren (${sponsoren.length})`}>
        <p className="mb-3 text-sm text-slate-600">
          Von eurer Website erkannt – aus dem Text und aus den Logos{vorschlag.sponsorenseite && <> auf <a className="text-teal-800 underline" href={vorschlag.sponsorenseite} target="_blank" rel="noreferrer">eurer Sponsorenseite</a></>}. Diese Unternehmen schlagen wir nicht noch einmal vor.
        </p>
        <ul className="divide-y divide-slate-100">
          {sponsoren.map((s, i) => (
            <li key={`${s.firma}-${i}`} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span className="flex min-w-0 items-center gap-3">
                {s.logo_url ? (
                  <img src={s.logo_url} alt="" className="h-8 w-14 shrink-0 rounded border border-slate-100 bg-white object-contain" loading="lazy" />
                ) : (
                  <span className="h-8 w-14 shrink-0" />
                )}
                <span className="min-w-0">
                  <span className="font-medium text-slate-800">{s.firma}</span>
                  {s.gegenleistung_text && <span className="text-slate-500"> – {s.gegenleistung_text}</span>}
                  {s.quelle === 'logo' && <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase text-slate-500">aus Logo</span>}
                </span>
              </span>
              <button className="text-xs text-slate-500 hover:text-red-700" onClick={() => setSponsoren(sponsoren.filter((_, j) => j !== i))}>
                entfernen
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input className={eingabe} value={neuerSponsor} onChange={(e) => setNeuerSponsor(e.target.value)} placeholder="Weiteren Sponsor eintragen" />
          <Knopf art="sekundaer" disabled={!neuerSponsor.trim()} onClick={() => { setSponsoren([...sponsoren, { firma: neuerSponsor.trim() }]); setNeuerSponsor('') }}>
            Hinzufügen
          </Knopf>
        </div>
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm">
          <p className="font-medium text-slate-700">Oder eure Sponsorenliste hochladen (CSV)</p>
          <p className="mb-2 text-xs text-slate-500">
            Spalten: firma; gegenleistung; betrag_eur; laufzeit_bis.{' '}
            <a className="text-teal-800 underline" href="https://github.com/6poiint9/Sandbox-Hackathon/blob/main/docs/vorlage-bestandssponsoren.csv" target="_blank" rel="noreferrer">Vorlage ansehen</a>
          </p>
          <input type="file" accept=".csv,text/csv" onChange={(e) => setCsv(e.target.files?.[0] ?? null)} className="text-sm" />
        </div>
      </Karte>

      <Karte titel="Was könnt ihr Sponsoren anbieten?">
        <p className="mb-3 text-sm text-slate-600">Haken setzen, was es bei euch gibt. Was schon vergeben ist, zählt nicht zum offenen Potenzial.</p>
        <div className="space-y-5">
          {Object.entries(kategorien).map(([kategorie, eintraege]) => (
            <div key={kategorie}>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{kategorie}</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {eintraege.map((e) => {
                  const wert = inventar[e.id] ?? 'nein'
                  return (
                    <div key={e.id} className={`rounded-lg border px-3 py-2 text-sm ${wert === 'nein' ? 'border-slate-200' : 'border-teal-600/40 bg-teal-50/40'}`}>
                      <label className="flex cursor-pointer items-start gap-2">
                        <input type="checkbox" className="mt-0.5 accent-teal-700" checked={wert !== 'nein'} onChange={(ev) => inventarSetzen(e.id, ev.target.checked ? 'frei' : 'nein')} />
                        <span className="text-slate-800">{e.name}</span>
                      </label>
                      {wert !== 'nein' && (
                        <label className="ml-6 mt-1 flex cursor-pointer items-center gap-2 text-xs text-slate-600">
                          <input type="checkbox" className="accent-slate-500" checked={wert === 'vergeben'} onChange={(ev) => inventarSetzen(e.id, ev.target.checked ? 'vergeben' : 'frei')} />
                          schon vergeben
                        </label>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </Karte>

      <div className="sticky bottom-0 -mx-4 flex flex-col gap-3 border-t border-slate-200 bg-slate-50/95 px-4 py-3 backdrop-blur sm:flex-row sm:items-center">
        <Knopf onClick={potenzialBerechnen} disabled={!!laedt}>Potenzialanalyse starten</Knopf>
        <Knopf art="leise" onClick={() => setVorschlag(null)} disabled={!!laedt}>Andere Website</Knopf>
        {laedt && <Lader text={laedt} />}
      </div>
      <Fehler text={fehler} />
    </div>
  )
}
