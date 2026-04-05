import { useEffect } from 'react'
import type { DetailTarget, PipelineState, Session, Task } from '../types'
import { getStepLabel, getStepColor, getStepOrder } from '../lib/pipeline'
import { formatElapsed, formatTimeAgo } from '../lib/time'
import { deleteResource } from '../lib/api'

interface DetailPanelProps {
  target: DetailTarget | null
  onClose: () => void
}

export default function DetailPanel({ target, onClose }: DetailPanelProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  if (!target) return null

  return (
    <div className="w-80 border-l border-gray-800 bg-gray-950 flex flex-col h-full overflow-y-auto">
      <div className="flex items-center justify-between p-3 border-b border-gray-800">
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
          {target.kind === 'step' ? 'Step Detail' :
           target.kind === 'pipeline' ? 'Pipeline Detail' :
           target.kind === 'session' ? 'Session Detail' : 'Task Detail'}
        </h3>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-sm">
          ✕
        </button>
      </div>

      <div className="p-3 flex-1">
        {target.kind === 'step' && <StepDetail pipeline={target.pipeline} stepName={target.stepName} />}
        {target.kind === 'pipeline' && <PipelineDetail pipeline={target.pipeline} onClose={onClose} />}
        {target.kind === 'session' && <SessionDetail session={target.session} />}
        {target.kind === 'task' && <TaskDetail task={target.task} />}
      </div>
    </div>
  )
}

function StepDetail({ pipeline, stepName }: { pipeline: PipelineState; stepName: string }) {
  const step = pipeline.steps[stepName]
  if (!step) return null

  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-sm font-medium text-gray-200">{getStepLabel(stepName)}</p>
        <p className="text-xs text-gray-500">{stepName}</p>
      </div>
      <Field label="Status">
        <span className="inline-flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${getStepColor(step.status)}`} />
          {step.status}
        </span>
      </Field>
      {step.value != null && (
        <Field label="Value">
          {typeof step.value === 'number' ? (
            <span>PR #{step.value}</span>
          ) : (
            <code className="text-xs bg-gray-900 px-1 rounded">{step.value}</code>
          )}
        </Field>
      )}
      {step.reason && <Field label="Reason">{step.reason}</Field>}
      {step.error && <Field label="Error"><span className="text-red-400">{step.error}</span></Field>}
      <Field label="Pipeline">#{pipeline.task_id} — {pipeline.title}</Field>
    </div>
  )
}

function PipelineDetail({ pipeline, onClose }: { pipeline: PipelineState; onClose: () => void }) {
  const steps = getStepOrder(pipeline.pipeline, pipeline.size)

  async function handleDismiss() {
    await deleteResource(`/pipeline-state/${pipeline.session_id}`)
    onClose()
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-sm font-medium text-gray-200">#{pipeline.task_id} {pipeline.title}</p>
        <p className="text-xs text-gray-500">{pipeline.pipeline}/{pipeline.size} · {pipeline.type}</p>
      </div>
      {pipeline.domain && <Field label="Domain">{pipeline.domain}</Field>}
      <Field label="Session">{pipeline.session_id.slice(0, 8)}</Field>
      <Field label="Started">{formatElapsed(pipeline.started_at)} ago</Field>
      {pipeline.heartbeat_at && (
        <Field label="Heartbeat">{formatTimeAgo(pipeline.heartbeat_at)}</Field>
      )}

      <div className="mt-2">
        <p className="text-xs text-gray-400 mb-2">Steps</p>
        <div className="flex flex-col gap-1">
          {steps.map((step) => {
            const state = pipeline.steps[step]
            if (!state) return null
            return (
              <div key={step} className="flex items-center gap-2 text-xs">
                <span className={`w-2 h-2 rounded-full ${getStepColor(state.status)}`} />
                <span className={state.status === 'skipped' ? 'text-gray-600 line-through' : 'text-gray-300'}>
                  {getStepLabel(step)}
                </span>
                {state.value != null && (
                  <span className="text-gray-500 ml-auto">
                    {typeof state.value === 'number' ? `#${state.value}` : String(state.value)}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {pipeline.stale && (
        <button
          onClick={handleDismiss}
          className="mt-4 w-full text-xs py-1.5 bg-amber-900/30 text-amber-400 rounded hover:bg-amber-900/50 transition-colors"
        >
          Dismiss stale pipeline
        </button>
      )}
    </div>
  )
}

function SessionDetail({ session }: { session: Session }) {
  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-sm font-medium text-gray-200">
          {session.name ?? `Session ${session.sessionId.slice(0, 8)}`}
        </p>
      </div>
      <Field label="ID">{session.sessionId.slice(0, 12)}</Field>
      <Field label="Status">{session.alive ? '● Alive' : '○ Dead'}</Field>
      <Field label="PID">{session.pid}</Field>
      <Field label="CWD"><code className="text-xs">{session.cwd}</code></Field>
      <Field label="Started">{formatElapsed(session.startedAt)} ago</Field>
      {session.task_id != null && <Field label="Task">#{session.task_id}</Field>}
      {session.heartbeat_at && <Field label="Heartbeat">{formatTimeAgo(session.heartbeat_at)}</Field>}
    </div>
  )
}

function TaskDetail({ task }: { task: Task }) {
  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-sm font-medium text-gray-200">#{task.id} {task.title}</p>
      </div>
      <Field label="Type">{task.type}</Field>
      <Field label="Priority">{task.priority}</Field>
      <Field label="Status">{task.status}</Field>
      {task.domain && <Field label="Domain">{task.domain}</Field>}
      {task.description && (
        <div>
          <p className="text-xs text-gray-400 mb-1">Description</p>
          <p className="text-xs text-gray-300">{task.description}</p>
        </div>
      )}
      {task.pr_number != null && <Field label="PR">#{task.pr_number}</Field>}
      {task.branch && <Field label="Branch"><code className="text-xs">{task.branch}</code></Field>}
      {task.spec_path && <Field label="Spec"><code className="text-xs">{task.spec_path}</code></Field>}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-xs text-gray-300">{children}</p>
    </div>
  )
}
