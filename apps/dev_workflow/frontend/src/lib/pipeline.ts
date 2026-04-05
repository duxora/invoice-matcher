import type { StepStatus, PipelineType, PipelineSize, PipelineState } from '../types'

const STEP_ORDER = {
  'code/small': ['kb_lookup', 'branch', 'implement', 'build', 'e2e_local', 'pr', 'ci', 'e2e_deploy', 'compact', 'handoff'] as const,
  'code/medium': ['kb_lookup', 'branch', 'implement', 'build', 'e2e_local', 'pr', 'ci', 'e2e_deploy', 'compact', 'handoff'] as const,
  'code/large': ['kb_lookup', 'brainstorm', 'write_plan', 'branch', 'implement', 'build', 'e2e_local', 'review', 'pr', 'ci', 'e2e_deploy', 'compact', 'handoff'] as const,
  research: ['kb_lookup', 'investigate', 'compact'] as const,
  docs: ['kb_lookup', 'write', 'compact'] as const,
  'solo-commit': ['kb_lookup', 'implement', 'build', 'compact'] as const,
} satisfies Record<string, readonly string[]>

const DEFAULT_ORDER = STEP_ORDER['code/medium']

export function getStepOrder(pipeline: PipelineType, size: PipelineSize): readonly string[] {
  const key = pipeline === 'code' ? `code/${size}` : pipeline
  if (key in STEP_ORDER) {
    return STEP_ORDER[key as keyof typeof STEP_ORDER]
  }
  return DEFAULT_ORDER
}

export function getActiveStep(pipeline: PipelineState): string | null {
  const order = getStepOrder(pipeline.pipeline, pipeline.size)
  for (const step of order) {
    const state = pipeline.steps[step]
    if (state?.status === 'failed') return step
    if (state?.status === 'pending') return step
  }
  return null
}

export function getStepColor(status: StepStatus | 'active' | 'stale'): string {
  switch (status) {
    case 'done':
      return 'bg-emerald-500'
    case 'active':
      return 'bg-blue-500'
    case 'pending':
      return 'bg-gray-600'
    case 'skipped':
      return 'bg-gray-700 opacity-40'
    case 'failed':
      return 'bg-red-500'
    case 'stale':
      return 'bg-amber-500'
  }
}

export function getLineColor(status: StepStatus | 'active' | 'stale'): string {
  switch (status) {
    case 'done':
      return 'bg-emerald-500'
    case 'failed':
      return 'bg-red-500'
    default:
      return 'bg-gray-700'
  }
}

const STEP_LABELS: Record<string, string> = {
  kb_lookup: 'KB',
  branch: 'Branch',
  brainstorm: 'Brain',
  write_plan: 'Plan',
  implement: 'Impl',
  build: 'Build',
  e2e_local: 'E2E',
  review: 'Review',
  pr: 'PR',
  ci: 'CI',
  e2e_deploy: 'Deploy',
  compact: 'Compact',
  handoff: 'Handoff',
  investigate: 'Research',
  write: 'Write',
}

export function getStepLabel(step: string): string {
  return STEP_LABELS[step] ?? step
}

export function getPipelineProgress(pipeline: PipelineState): { done: number; total: number } {
  const order = getStepOrder(pipeline.pipeline, pipeline.size)
  let done = 0
  let total = 0
  for (const step of order) {
    const state = pipeline.steps[step]
    if (state?.status === 'skipped') continue
    total++
    if (state?.status === 'done') done++
  }
  return { done, total }
}
