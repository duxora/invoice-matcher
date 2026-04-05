/** API client for the Telegram Bridge backend. */

const BASE = '/telegram-bridge'

export interface HealthResponse {
  running: boolean
  service: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/health`)
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`)
  return res.json() as Promise<HealthResponse>
}

export async function restartBot(): Promise<void> {
  const res = await fetch(`${BASE}/restart`, { method: 'POST' })
  if (!res.ok) throw new Error(`Restart failed: ${res.status} ${res.statusText}`)
}

/**
 * Fetches the logs HTML partial and extracts the plain-text log lines from
 * the <pre> element.  Returns raw text so the React component can render it.
 */
export async function fetchLogs(): Promise<string> {
  const res = await fetch(`${BASE}/partials/logs`)
  if (!res.ok) throw new Error(`Logs fetch failed: ${res.status} ${res.statusText}`)
  const html = await res.text()
  // Strip the wrapping <pre ...>…</pre> tags; keep inner text
  const match = html.match(/<pre[^>]*>([\s\S]*?)<\/pre>/i)
  return match?.[1] ?? html
}
