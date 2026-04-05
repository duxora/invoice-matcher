import useSWR from 'swr'
import { fetchJson } from '../lib/api'
import type { Session } from '../types'

export function useSessions() {
  const { data, error, isLoading } = useSWR<Session[]>(
    '/sessions',
    fetchJson<Session[]>,
    { refreshInterval: 5000 },
  )
  return {
    sessions: data ?? [],
    error,
    isLoading,
  }
}
