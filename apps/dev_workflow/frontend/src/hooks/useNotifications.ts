import { useRef, useEffect } from 'react'
import type { PipelineState } from '../types'
import { requestPermission, detectTransitions } from '../lib/notifications'

export function useNotifications(pipelines: PipelineState[]): void {
  const prevRef = useRef<PipelineState[]>([])

  useEffect(() => {
    requestPermission()
  }, [])

  useEffect(() => {
    if (prevRef.current.length > 0) {
      detectTransitions(prevRef.current, pipelines)
    }
    prevRef.current = pipelines
  }, [pipelines])
}
