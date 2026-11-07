import { useEffect, useState } from 'react'
import { api, euro, STATUS_TEXT } from '../api'
import Verlauf from '../components/Verlauf'
import type { Ansprache, Kandidat, KandidatStatus } from '../api'
import { Fehler, Feld, Karte, Knopf, Lader, ScoreBadge, eingabe } from '../components/ui'

type Reiter = 'brief' | 'leitfaden' | 'email'

export default function Detail({ vereinId, kandidatId, onZurueck }: { vereinId: number; kandidatId: number; onZurueck: () => void }) {
  const [k, setK] = useState<Kandidat | null>(null)
  const [ansprache, setAnsprache] = useState<Ansprache | null>(null)
  const [reiter, setReiter] = useState<Reiter>('brief')
  const [laedt, setLaedt] = useState(false)
  const [fehler, setFehler] = useState<string | null>(null)
  const [kopiert, setKopiert] = useState(false)
  const [verlauf, setVerlauf] = useState(0)

  useEffect(() => {
    api.get<Kandidat[]>(`/vereine/${vereinId}/kandidaten`)
      .then((alle) => setK(alle.find((x) => x.id === kandidatId) ?? null))
      .catch((e: Error) => setFehler(e.message))
    api.get<Ansprache>(`/kandidaten/${kandidatId}/ansprache`).then(setAnsprache).catch(() => setAnsprache(null))
  }, [vereinId, kandidatId])

  async function anspracheErzeugen(neu = false) {
    setLaedt(true)
    setFehler(null)
    try {
      setAnsprache(await api.post<Ansprache>(`/kandidaten/${kandidatId}/ansprache${neu ? '?neu=true' : ''}`))
    } catch (e) {
      setFehler((e as Error).message)
    } finally {
      setLaedt(false)
    }
  }

  async function statusSetzen(status: KandidatStatus) {
    try {
      setK(await api.patch<Kandidat>(`/kandidaten/${kandidatId}/status`, { status }))
      setVerlauf((n) => n + 1)
    } catch (e) {
      setFehler((e as Error).message)
    }
  }

  async function recherchieren() {
    // Recherche für genau diesen Kandidaten anstoßen und warten
    setLaedt(true)
    try {
      await api.post(`/vereine/${vereinId}/recherche?anzahl=1&kandidat_id=${kandidatId}`)
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => setTimeout(r, 1500))
        const alle = await api.get<Kandidat[]>(`/vereine/${vereinId}/kandidaten`)
        const neu = alle.find((x) => x.id === kandidatId)
        if (neu && neu.recherche_status !== 'wartet' && neu.recherche_status !== 'laeuft') {
          setK(neu)
          break
        }
      }
    } finally {
      setLaedt(false)
    }
  }

  const text = ansprache
    ? { brief: ansprache.brief, leitfaden: ansprache.leitfaden, email: `Betreff: ${ansprache.email_betreff}\n\n${ansprache.email_text}` }[reiter]
    : ''

  async function kopieren() {
    try {
      await navigator.clipboard.writeText(text)
      setKopiert(true)
      setTimeout(() => setKopiert(false), 1500)
    } catch {
      setFehler('Kopieren nicht möglich – bitte Text markieren und kopieren.')
    }
  }

  if (!k) return fehler ? <Fehler text={fehler} /> : <Lader text="Kandidat wird geladen …" />
  const u = k.unternehmen
  const geprueft = k.recherche_status === 'fertig'
  const pe = k.paket_empfehlung

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <button className="text-sm text-rasen-800 hover:underline" onClick={onZurueck}>← Zur Potenzialanalyse</button>

      <Karte>
        <div className="flex items-start gap-4">
          <ScoreBadge score={geprueft ? k.score : k.vorfilter_score} vorlaeufig={!geprueft} />
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-semibold text-stein-900">{u.name}</h1>
            <p className="text-sm text-stein-600">
              {u.branche}, {k.entfernung_km.toLocaleString('de-DE')} km{u.adresse ? `, ${u.adresse}` : ''}
            </p>
            {u.website && <a className="break-all text-sm text-rasen-800 underline" href={u.website} target="_blank" rel="noreferrer">{u.website}</a>}
            {k.zusammenfassung && <p className="mt-3 text-stein-700">{k.zusammenfassung}</p>}
            {geprueft && k.sicherheit && (
              <p className="mt-2 text-xs text-stein-500">
                Sicherheit der Bewertung: <span className="font-medium">{k.sicherheit}</span>
                {k.sicherheit === 'niedrig' && ' – wenig belegte Informationen gefunden'}
              </p>
            )}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(Object.keys(STATUS_TEXT) as KandidatStatus[]).map((s) => (
            <button
              key={s}
              onClick={() => statusSetzen(s)}
              className={`rounded-full px-3 py-1 text-xs font-medium ${k.status === s ? 'bg-rasen-700 text-white' : 'bg-stein-100 text-stein-700 hover:bg-stein-200'}`}
            >
              {STATUS_TEXT[s]}
            </button>
          ))}
        </div>
      </Karte>

      {!geprueft ? (
        <Karte titel="Noch nicht recherchiert">
          <ul className="mb-3 list-disc pl-5 text-sm text-stein-600">{k.vorfilter_gruende.map((g) => <li key={g}>{g}</li>)}</ul>
          {k.recherche_fehler && <Fehler text={k.recherche_fehler} />}
          <Knopf onClick={recherchieren} disabled={laedt}>Jetzt mit Quellen prüfen</Knopf>
          {laedt && <div className="mt-2"><Lader text="Website und Web werden durchsucht …" /></div>}
        </Karte>
      ) : (
        <>
          <Karte titel="Warum dieses Unternehmen?">
            <ol className="space-y-3">
              {k.gruende.map((g, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-rasen-100 text-xs font-semibold text-rasen-900">{i + 1}</span>
                  <span className="min-w-0">
                    <span className="text-stein-800">{g.text}</span>
                    <a className="block truncate text-xs text-rasen-800 underline" href={g.quelle_url} target="_blank" rel="noreferrer">
                      Quelle: {g.quelle_url.replace(/^https?:\/\/(www\.)?/, '')}
                    </a>
                  </span>
                </li>
              ))}
            </ol>
          </Karte>

          <Karte titel="Empfohlenes Angebot">
            <p className="text-lg font-semibold text-stein-900">{(pe.namen ?? []).join(' + ') || '–'}</p>
            {pe.preis_eur && <p className="text-rasen-800">{euro(pe.preis_eur.min)} – {euro(pe.preis_eur.max)} pro Saison <span className="text-xs text-stein-500">(Richtwert)</span></p>}
            {pe.begruendung && <p className="mt-2 text-sm text-stein-600">{pe.begruendung}</p>}
          </Karte>

          <Karte titel="Ansprache">
            {!ansprache ? (
              <div className="space-y-2">
                <p className="text-sm text-stein-600">Persönlicher Brief, Leitfaden fürs Telefonat und eine E-Mail für nach dem Erstkontakt – mit Bezug auf die Gründe oben.</p>
                <Knopf onClick={() => anspracheErzeugen()} disabled={laedt}>Ansprache erstellen</Knopf>
                {laedt && <Lader text="Brief wird geschrieben …" />}
              </div>
            ) : (
              <>
                <div className="mb-3 flex flex-wrap gap-1 border-b border-stein-200">
                  {([['brief', 'Brief'], ['leitfaden', 'Telefonleitfaden'], ['email', 'E-Mail nach Erstkontakt']] as [Reiter, string][]).map(([r, t]) => (
                    <button
                      key={r}
                      onClick={() => setReiter(r)}
                      className={`-mb-px border-b-2 px-3 py-2 text-sm ${reiter === r ? 'border-rasen-700 font-medium text-rasen-900' : 'border-transparent text-stein-500 hover:text-stein-800'}`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
                <pre className="whitespace-pre-wrap rounded-lg bg-stein-50 p-4 font-sans text-sm leading-relaxed text-stein-800">{text}</pre>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Knopf onClick={kopieren}>{kopiert ? 'Kopiert ✓' : 'Kopieren'}</Knopf>
                  <Knopf art="leise" onClick={() => anspracheErzeugen(true)} disabled={laedt}>Neu formulieren</Knopf>
                  {laedt && <Lader text="Wird neu geschrieben …" />}
                </div>
                <p className="mt-3 text-xs text-stein-500">
                  Hinweis: Erst Brief oder Anruf, die E-Mail nach dem Gespräch. Sponsorenkompass versendet nichts selbst.
                </p>
              </>
            )}
          </Karte>
        </>
      )}
      <CrmKarte k={k} vereinId={vereinId} onAenderung={(neu) => { setK(neu); setVerlauf((n) => n + 1) }} verlauf={verlauf} />
      <Fehler text={fehler} />
    </div>
  )
}

function CrmKarte({ k, vereinId, onAenderung, verlauf }: { k: Kandidat; vereinId: number; onAenderung: (k: Kandidat) => void; verlauf: number }) {
  const [f, setF] = useState({
    ansprechpartner: k.ansprechpartner ?? '',
    email: k.email ?? '',
    telefon: k.telefon ?? '',
    naechster_schritt: k.naechster_schritt ?? '',
    wiedervorlage: k.wiedervorlage ?? '',
    notiz: k.notiz ?? '',
  })
  const [meldung, setMeldung] = useState<string | null>(null)
  const [betrag, setBetrag] = useState(k.paket_empfehlung.preis_eur ? String(k.paket_empfehlung.preis_eur.min) : '')
  const set = (feld: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [feld]: e.target.value })

  async function speichern() {
    const daten = Object.fromEntries(Object.entries(f).map(([a, b]) => [a, b.trim() === '' ? null : b]))
    await api.patch(`/kandidaten/${k.id}`, daten)
    const alle = await api.get<Kandidat[]>(`/vereine/${vereinId}/kandidaten`)
    const neu = alle.find((x) => x.id === k.id)
    if (neu) onAenderung(neu)
    setMeldung('Gespeichert ✓')
  }

  async function uebernehmen() {
    await api.post(`/kandidaten/${k.id}/zum-sponsor`, { betrag_eur: betrag ? Number(betrag.replace(/\D/g, '')) : null })
    const alle = await api.get<Kandidat[]>(`/vereine/${vereinId}/kandidaten`)
    const neu = alle.find((x) => x.id === k.id)
    if (neu) onAenderung(neu)
    setMeldung('Als Sponsor übernommen ✓ – zu finden unter „Sponsoren“')
  }

  return (
    <Karte titel="Kontakt und Nachverfolgung">
      <div className="grid gap-3 sm:grid-cols-3">
        <Feld label="Ansprechpartner"><input className={eingabe} value={f.ansprechpartner} onChange={set('ansprechpartner')} /></Feld>
        <Feld label="E-Mail"><input type="email" className={eingabe} value={f.email} onChange={set('email')} /></Feld>
        <Feld label="Telefon"><input className={eingabe} value={f.telefon} onChange={set('telefon')} /></Feld>
        <Feld label="Nächster Schritt"><input className={eingabe} value={f.naechster_schritt} onChange={set('naechster_schritt')} placeholder="z. B. Nachfassen nach Brief" /></Feld>
        <Feld label="Wiedervorlage am"><input type="date" className={eingabe} value={f.wiedervorlage} onChange={set('wiedervorlage')} /></Feld>
        <Feld label="Notiz"><input className={eingabe} value={f.notiz} onChange={set('notiz')} /></Feld>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Knopf art="sekundaer" onClick={speichern}>Speichern</Knopf>
        {meldung && <span className="text-sm text-stein-600">{meldung}</span>}
      </div>
      {k.status === 'zusage' && !k.sponsor_id && (
        <div className="mt-4 flex flex-col gap-2 rounded-lg bg-rasen-50 p-3 sm:flex-row sm:items-end">
          <Feld label="Vereinbarter Betrag pro Saison (€)"><input className={eingabe} inputMode="numeric" value={betrag} onChange={(e) => setBetrag(e.target.value)} /></Feld>
          <Knopf onClick={uebernehmen}>Als Sponsor übernehmen</Knopf>
        </div>
      )}
      {k.sponsor_id && <p className="mt-3 text-sm text-rasen-800">✓ Als Sponsor im Bestand.</p>}
      <div className="mt-5">
        <p className="mb-2 text-sm font-semibold text-stein-700">Verlauf</p>
        <Verlauf vereinId={vereinId} kandidatId={k.id} neuLaden={verlauf} />
      </div>
    </Karte>
  )
}
