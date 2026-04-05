import type { KBEntry, KBStats, KBDomain, KBSourcesByDomain } from '../types'

const BASE = '/kb'

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export async function fetchStats(): Promise<KBStats> {
  return fetchJson<KBStats>('/api/stats')
}

export async function searchEntries({
  q,
  domain,
}: {
  q: string
  domain?: string
}): Promise<KBEntry[]> {
  const params = new URLSearchParams({ q })
  if (domain) params.set('domain', domain)
  return fetchJson<KBEntry[]>(`/api/search?${params}`)
}

export async function deleteEntry(entryId: string): Promise<void> {
  const res = await fetch(`${BASE}/entry/${entryId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`DELETE error: ${res.status} ${res.statusText}`)
}

export async function ingestUrl({
  url,
  domain,
}: {
  url: string
  domain: KBDomain
}): Promise<{ ok: boolean; message: string }> {
  const body = new URLSearchParams({ url, domain })
  const res = await fetch(`${BASE}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  })
  const text = await res.text()
  // The backend returns HTML snippets. Parse success/error from text content.
  if (text.includes('text-green-400') || text.includes('Ingested:')) {
    const titleMatch = text.match(/<strong>(.*?)<\/strong>/)
    const title = titleMatch ? titleMatch[1] : ''
    return { ok: true, message: title ? `Ingested: ${title}` : 'Ingested successfully' }
  }
  if (text.includes('already indexed')) {
    return { ok: false, message: 'URL already indexed.' }
  }
  if (text.includes('Failed to fetch')) {
    return { ok: false, message: `Failed to fetch: ${url}` }
  }
  if (text.includes('too thin')) {
    return { ok: false, message: 'Content too thin to distill.' }
  }
  return { ok: false, message: text.replace(/<[^>]*>/g, '').trim() }
}

export async function ingestAll(): Promise<string> {
  const res = await fetch(`${BASE}/ingest-all`, { method: 'POST' })
  const text = await res.text()
  return text.replace(/<[^>]*>/g, '').trim()
}

export async function fetchSources(): Promise<KBSourcesByDomain> {
  // Sources are only available as HTML from the Jinja route.
  // We expose them via the sources page which reads the YAML server-side.
  // For the React version we call the existing route and parse, OR we add an
  // API endpoint. Since we cannot modify the backend, we fetch the HTML and
  // extract nothing useful — instead we return an empty object and show a
  // message instructing to use the CLI.
  // NOTE: If a /kb/api/sources endpoint is added later, swap this out.
  return {}
}
