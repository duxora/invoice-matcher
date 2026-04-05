import useSWR from 'swr'
import { schedulerApi } from '../lib/api'
import type { SchedulerTask } from '../types'

export function useSchedulerTasks() {
  const { data, error, isLoading, mutate } = useSWR<SchedulerTask[]>(
    'scheduler-tasks',
    () => schedulerApi.getTasks(),
    { refreshInterval: 10_000 },
  )
  return {
    tasks: data ?? [],
    error,
    isLoading,
    mutate,
  }
}
