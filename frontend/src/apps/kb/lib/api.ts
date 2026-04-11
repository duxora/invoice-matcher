import type { KBEntry, KBStats, KBDomain, KBSourcesByDomain } from '../types'

const BASE = '/kb'

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export async function fetchStats(): Promise<KBStats> {
  return fetchJson<KBStats>('/api/stats')
}

export async function getEntry(id: string): Promise<KBEntry> {
  return fetchJson<KBEntry>(`/api/entry/${encodeURIComponent(id)}`)
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
  const res = await fetch(`${BASE}/api/entry/${encodeURIComponent(entryId)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`DELETE error: ${res.status} ${res.statusText}`)
}

export async function ingestUrl({
  url,
  domain,
}: {
  url: string
  domain: KBDomain
}): Promise<{ ok: boolean; message: string; entry_id?: string; title?: string }> {
  return fetchJson('/api/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, domain }),
  })
}

export async function ingestAll(): Promise<string> {
  const res = await fetchJson<{ ok: boolean; output: string }>('/api/ingest-all', { method: 'POST' })
  return res.output
}

export async function fetchSources(): Promise<KBSourcesByDomain> {
  return fetchJson<KBSourcesByDomain>('/api/sources')
}
