import type { PipelineState } from '../types'
import { getPipelineProgress } from './pipeline'

export function requestPermission(): void {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
}

export function canNotify(): boolean {
  return 'Notification' in window && Notification.permission === 'granted'
}

function notify(title: string, body: string): void {
  if (!canNotify()) return
  new Notification(title, { body })
}

export function detectTransitions(
  prev: PipelineState[],
  next: PipelineState[],
): void {
  const prevMap = new Map(prev.map((p) => [p.session_id, p]))

  for (const pipeline of next) {
    const old = prevMap.get(pipeline.session_id)
    if (!old) continue

    const { done, total } = getPipelineProgress(pipeline)
    const oldProgress = getPipelineProgress(old)
    if (done === total && oldProgress.done < oldProgress.total) {
      notify('Pipeline complete', `#${pipeline.task_id} ${pipeline.title}`)
    }

    for (const [step, state] of Object.entries(pipeline.steps)) {
      const oldStep = old.steps[step]
      if (state.status === 'failed' && oldStep?.status !== 'failed') {
        notify('Step failed', `${step}: #${pipeline.task_id} ${pipeline.title}`)
      }
    }

    if (pipeline.stale && !old.stale) {
      notify('Agent unresponsive', `#${pipeline.task_id} — no heartbeat`)
    }
  }
}
