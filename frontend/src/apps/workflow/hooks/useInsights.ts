import useSWR from 'swr'
import { fetchJson } from '../lib/api'
import type { InsightsResponse } from '../types'

interface InsightsParams {
  pipeline?: string
  size?: string
  period?: string
}

export function useInsights({ pipeline, size, period }: InsightsParams = {}) {
  const params = new URLSearchParams()
  if (pipeline) params.set('pipeline', pipeline)
  if (size) params.set('size', size)
  if (period) params.set('period', period)
  const query = params.toString()
  const key = `/insights${query ? `?${query}` : ''}`

  const { data, error, isLoading } = useSWR<InsightsResponse>(
    key,
    fetchJson<InsightsResponse>,
    { refreshInterval: 30_000 },
  )

  return {
    data,
    error,
    isLoading,
  }
}
