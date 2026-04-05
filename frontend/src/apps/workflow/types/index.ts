export type StepStatus = 'done' | 'pending' | 'skipped' | 'failed'

export interface StepState {
  status: StepStatus
  value?: string | number
  reason?: string
  error?: string
}

export type PipelineType = 'code' | 'research' | 'docs' | 'solo-commit'
export type PipelineSize = 'small' | 'medium' | 'large'

export interface PipelineState {
  task_id: number
  title: string
  type: string
  domain: string | null
  session_id: string
  pipeline: PipelineType
  size: PipelineSize
  started_at: string
  heartbeat_at: string | null
  stale: boolean
  steps: Record<string, StepState>
}

export interface PipelineStateResponse {
  pipelines: PipelineState[]
}

export interface Session {
  sessionId: string
  pid: number
  alive: boolean
  cwd: string
  startedAt: string
  name: string | null
  task_id: number | null
  heartbeat_at: string | null
}

export interface Task {
  id: number
  title: string
  type: string
  priority: string
  status: string
  domain: string | null
  project_id: string
  project_name: string
  pr_number: number | null
  branch: string | null
  spec_path: string | null
  description: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
  phase: string
}

export interface ProjectSummary {
  project_id: string
  project_name: string
  open_count: number
  in_progress_count: number
  done_count: number
}

export type DetailTarget =
  | { kind: 'step'; pipeline: PipelineState; stepName: string }
  | { kind: 'pipeline'; pipeline: PipelineState }
  | { kind: 'session'; session: Session }
  | { kind: 'task'; task: Task }
