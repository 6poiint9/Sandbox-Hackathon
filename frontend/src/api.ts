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
  delete: (pfad: string) => anfrage<void>(pfad, { method: 'DELETE' }),
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

export type SponsorStatus = 'aktiv' | 'verlaengerung' | 'beendet'

export type Sponsor = {
  id: number
  firma: string
  website: string | null
  gegenleistung: string | null
  gegenleistung_text: string | null
  betrag_eur: number | null
  laufzeit_bis: string | null
  ansprechpartner: string | null
  email: string | null
  telefon: string | null
  status: SponsorStatus | null
  naechster_schritt: string | null
  wiedervorlage: string | null
  logo_url: string | null
  notiz: string | null
}

export const SPONSOR_STATUS_TEXT: Record<SponsorStatus, string> = {
  aktiv: 'Aktiv',
  verlaengerung: 'Verlängerung offen',
  beendet: 'Beendet',
}

export type AktivitaetArt = 'notiz' | 'anruf' | 'brief' | 'email' | 'treffen' | 'status' | 'vertrag'

export type Aktivitaet = {
  id: number
  art: AktivitaetArt
  text: string
  zeitpunkt: string
  sponsor_id: number | null
  kandidat_id: number | null
}

export const AKTIVITAET_TEXT: Record<AktivitaetArt, string> = {
  notiz: 'Notiz',
  anruf: 'Anruf',
  brief: 'Brief',
  email: 'E-Mail',
  treffen: 'Treffen',
  status: 'Status',
  vertrag: 'Vertrag',
}

export type Aufgabe = {
  art: 'wiedervorlage' | 'vertragsende'
  faellig: string
  titel: string
  text: string
  sponsor_id: number | null
  kandidat_id: number | null
  ueberfaellig: boolean
}

export type AssetAnsicht = {
  id: number
  katalog_id: string
  name: string
  kategorie: string
  gegenleistung: string
  beschreibung: string | null
  anzahl: number
  belegt: number
  frei: number
  preis_eur: number | null
  richtpreis: { min: number; max: number } | null
  einnahmen_eur: number
  vergaben: { id: number; sponsor_id: number; sponsor: string; anzahl: number; preis_eur: number | null; bis: string | null }[]
}

export const datum = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleDateString('de-DE') : '–')

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
  ansprechpartner: string | null
  email: string | null
  telefon: string | null
  naechster_schritt: string | null
  wiedervorlage: string | null
  notiz: string | null
  sponsor_id: number | null
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

export type AnalyseZustand = {
  suche_status: 'offen' | 'laeuft' | 'fertig' | 'fehler'
  suche_fehler: string | null
  benachrichtigung_email: string | null
  email_verfuegbar: boolean
  recherche: RechercheStatus
}

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
