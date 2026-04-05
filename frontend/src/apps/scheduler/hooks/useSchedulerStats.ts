import useSWR from 'swr'
import { schedulerApi } from '../lib/api'
import type { SchedulerStats } from '../types'

export function useSchedulerStats() {
  const { data, error, isLoading } = useSWR<SchedulerStats>(
    'scheduler-stats',
    () => schedulerApi.getStats(),
    { refreshInterval: 10_000 },
  )
  return {
    stats: data ?? null,
    error,
    isLoading,
  }
}
