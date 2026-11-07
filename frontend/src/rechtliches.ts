// Angaben für Impressum und Datenschutzerklärung – an EINER Stelle pflegen.
// Alles in [eckigen Klammern] vor dem Livegang ersetzen. Solange Platzhalter
// enthalten sind, zeigen beide Seiten einen gut sichtbaren Hinweis.

export const ANBIETER = {
  name: '[Vor- und Nachname bzw. Firma]',
  strasse: '[Straße und Hausnummer]',
  plzOrt: '[PLZ Ort]',
  land: 'Deutschland',
  email: '[kontakt@ihre-domain.de]',
  telefon: '', // optional, z. B. '+49 …'
  // Inhaltlich verantwortlich nach § 18 Abs. 2 MStV (Name + Anschrift, falls abweichend)
  verantwortlichInhalt: '[Vor- und Nachname, Anschrift wie oben]',
  // Sobald vorhanden: Rechtsform, Registergericht, Registernummer, USt-IdNr.
  zusatz: [] as string[],
}

// Hosting-Anbieter eintragen, sobald entschieden (Auftragsverarbeitungsvertrag abschließen!)
export const HOSTING = '[Hosting-Anbieter, Sitz, Serverstandort]'

// Zuständige Datenschutz-Aufsichtsbehörde (Bundesland des Anbieters)
export const AUFSICHT = '[z. B. Landesbeauftragte/r für Datenschutz und Informationsfreiheit Baden-Württemberg]'

export const STAND = '7. November 2026'

export const hatPlatzhalter = (): boolean =>
  JSON.stringify({ ANBIETER, HOSTING, AUFSICHT }).includes('[')
