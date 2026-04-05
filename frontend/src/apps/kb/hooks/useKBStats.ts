import useSWR from 'swr'
import type { KBStats } from '../types'

const fetcher = (url: string) => fetch(url).then((r) => r.json())

export function useKBStats() {
  const { data, error, isLoading, mutate } = useSWR<KBStats>(
    '/kb/api/stats',
    fetcher,
    { refreshInterval: 30_000 },
  )

  return {
    stats: data,
    error,
    isLoading,
    refresh: mutate,
  }
}
