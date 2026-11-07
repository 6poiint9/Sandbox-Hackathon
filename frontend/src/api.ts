export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function anfrage<T>(pfad: string, init?: RequestInit): Promise<T> {
  const antwort = await fetch(`${API_URL}${pfad}`, init)
  if (!antwort.ok) {
    let detail = `HTTP ${antwort.status}`
    try {
      const daten = await antwort.json()
      if (daten?.detail) detail = typeof daten.detail === 'string' ? daten.detail : JSON.stringify(daten.detail)
    } catch {
      /* keine JSON-Antwort */
    }
    throw new Error(detail)
  }
  if (antwort.status === 204) return undefined as T
  return antwort.json() as Promise<T>
}

const json = (methode: string, daten: unknown): RequestInit => ({
  method: methode,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(daten),
})

export const api = {
  get: <T>(pfad: string) => anfrage<T>(pfad),
  post: <T>(pfad: string, daten?: unknown) => anfrage<T>(pfad, json('POST', daten ?? {})),
  put: <T>(pfad: string, daten: unknown) => anfrage<T>(pfad, json('PUT', daten)),
  patch: <T>(pfad: string, daten: unknown) => anfrage<T>(pfad, json('PATCH', daten)),
  upload: <T>(pfad: string, datei: File) => {
    const form = new FormData()
    form.append('datei', datei)
    return anfrage<T>(pfad, { method: 'POST', body: form })
  },
}

// ---- Typen (Feldnamen wie im Backend) -------------------------------------

export type Mannschaft = { name: string; spielklasse?: string | null }

export type Beleg = { feld: string; urls: string[]; sicherheit: string }

export type ErkannterSponsor = {
  firma: string
  gegenleistung_text?: string | null
  gegenleistung?: string | null
  website?: string | null
  logo_url?: string | null
  quelle?: 'text' | 'logo' | 'text+logo'
}

export type ProfilVorschlag = {
  name: string | null
  website: string
  ort: string
  sportstaette: string | null
  lat: number | null
  lon: number | null
  sponsorenseite: string | null
  sportarten: string[]
  mannschaften: Mannschaft[]
  spielklasse: string | null
  mitglieder: number | null
  veranstaltungen: string[]
  sponsoren: ErkannterSponsor[]
  inventar_vergeben: string[]
  belege: Beleg[]
  hinweise: string[]
}

export type Verein = {
  id: number
  name: string
  website: string | null
  ort: string
  lat: number | null
  lon: number | null
  sportarten: string[]
  mannschaften: Mannschaft[]
  spielklasse: string | null
  mitglieder: number | null
  zuschauer_schnitt: number | null
  veranstaltungen: string[]
  radius_km: number
  luecken: { branche: string; betriebe: number }[]
  betriebe_im_umkreis: number | null
}

export type KatalogEintrag = {
  id: string
  kategorie: string
  name: string
  gegenleistung: string
  zielbranchen: string[]
  preis_min: number | null
  preis_max: number | null
  einheit: string
  quelle: string
}

export type Sponsor = {
  id: number
  firma: string
  website: string | null
  gegenleistung: string | null
  gegenleistung_text: string | null
  betrag_eur: number | null
  laufzeit_bis: string | null
  notiz: string | null
}

export type Unternehmen = {
  id: number
  name: string
  branche: string
  adresse: string | null
  lat: number
  lon: number
  website: string | null
}

export type KandidatStatus = 'neu' | 'kontaktiert' | 'termin' | 'zusage' | 'absage'

export type Kandidat = {
  id: number
  status: KandidatStatus
  entfernung_km: number
  vorfilter_score: number
  vorfilter_gruende: string[]
  score: number | null
  sicherheit: 'niedrig' | 'mittel' | 'hoch' | null
  gruende: { text: string; quelle_url: string }[]
  paket_empfehlung: {
    katalog_ids?: string[]
    namen?: string[]
    preis_eur?: { min: number; max: number } | null
    begruendung?: string
    passende_pakete?: string[]
  }
  zusammenfassung: string | null
  quellen: { url: string; titel: string | null }[]
  recherche_status: 'offen' | 'wartet' | 'laeuft' | 'fertig' | 'fehler'
  recherche_fehler: string | null
  unternehmen: Unternehmen
}

export type Paket = {
  katalog_id: string
  name: string
  kategorie: string
  min: number
  max: number
  menge: number
  annahme: string | null
  quelle: string
  eigener_preis: boolean
}

export type Potenzial = {
  spanne_min: number
  spanne_max: number
  freie_pakete: Paket[]
  sachleistungen: string[]
  vergebene_pakete: { katalog_id: string; name: string; sponsor: string | null }[]
  bestand_eur: number
  bestand_sponsoren: number
  luecken: { branche: string; betriebe: number }[]
  betriebe_im_umkreis: number | null
  annahmen: string[]
  hinweis: string
}

export type RechercheStatus = { gesamt: number; status: Record<string, number>; fertig: boolean }

export type Ansprache = {
  id: number
  kandidat_id: number
  brief: string
  leitfaden: string
  email_betreff: string
  email_text: string
}

export const STATUS_TEXT: Record<KandidatStatus, string> = {
  neu: 'Neu',
  kontaktiert: 'Kontaktiert',
  termin: 'Termin',
  zusage: 'Zusage',
  absage: 'Absage',
}

export const euro = (n: number) => n.toLocaleString('de-DE') + ' €'
