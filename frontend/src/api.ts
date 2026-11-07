export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function apiGet<T>(pfad: string): Promise<T> {
  const antwort = await fetch(`${API_URL}${pfad}`)
  if (!antwort.ok) throw new Error(`${pfad}: HTTP ${antwort.status}`)
  return antwort.json() as Promise<T>
}
