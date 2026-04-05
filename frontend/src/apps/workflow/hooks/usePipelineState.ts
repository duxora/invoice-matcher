import useSWR from 'swr'
import { fetchJson } from '../lib/api'
import type { PipelineStateResponse } from '../types'

export function usePipelineState() {
  const { data, error, isLoading } = useSWR<PipelineStateResponse>(
    '/pipeline-state',
    fetchJson<PipelineStateResponse>,
    { refreshInterval: 3000 },
  )
  return {
    pipelines: data?.pipelines ?? [],
    error,
    isLoading,
  }
}
