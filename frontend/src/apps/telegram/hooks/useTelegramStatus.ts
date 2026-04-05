import useSWR from 'swr'
import { fetchHealth } from '../lib/api'
import type { HealthResponse } from '../lib/api'

/**
 * Polls the Telegram Bridge health endpoint every 10 seconds.
 * Returns running state, the launchd service label, and loading/error state.
 */
export function useTelegramStatus() {
  const { data, error, isLoading, mutate } = useSWR<HealthResponse>(
    'telegram-health',
    fetchHealth,
    { refreshInterval: 10_000 },
  )

  return {
    running: data?.running ?? false,
    service: data?.service ?? '',
    isLoading,
    error: error as Error | undefined,
    refresh: mutate,
  }
}
