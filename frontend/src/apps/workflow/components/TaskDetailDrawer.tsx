import { useEffect } from 'react'
import useSWR from 'swr'

// ── types ──────────────────────────────────────────────────────────────────

interface TaskDetail {
  id: number
  title: string
  description: string | null
  type: string
  priority: string
  status: string
  domain: string | null
  pr_number: number | null
  branch: string | null
  project_name: string
  repo_path: string | null
  spec_path: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

interface HistoryStep {
  label: string
  timestamp: string
  field: string
}

interface Note {
  content: string
  added_by: string
  created_at: string
}

interface Doc {
  type: 'spec' | 'reference'
  path: string
}

interface TaskDetailResponse {
  task: TaskDetail
  steps: HistoryStep[]
  notes: Note[]
  docs: Doc[]
}

// ── constants ──────────────────────────────────────────────────────────────

const PRIORITY_BADGE: Record<string, string> = {
  critical: 'bg-red-950 text-red-400 border border-red-800',
  high: 'bg-orange-950 text-orange-400 border border-orange-800',
  medium: 'bg-yellow-950 text-yellow-400 border border-yellow-800',
  low: 'bg-gray-800 text-gray-500 border border-gray-700',
}

const STATUS_BADGE: Record<string, string> = {
  open: 'bg-blue-950 text-blue-400 border border-blue-800',
  in_progress: 'bg-amber-950 text-amber-400 border border-amber-800',
  backlog: 'bg-indigo-950 text-indigo-400 border border-indigo-800',
  done: 'bg-green-950 text-green-400 border border-green-800',
}

// ── fetcher ────────────────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then((r) => r.json())

// ── helpers ────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">{label}</p>
      <p className="text-xs text-gray-300">{children}</p>
    </div>
  )
}

// ── main component ─────────────────────────────────────────────────────────

interface TaskDetailDrawerProps {
  taskId: number | null
  onClose: () => void
}

export default function TaskDetailDrawer({ taskId, onClose }: TaskDetailDrawerProps) {
  const { data, error } = useSWR<TaskDetailResponse>(
    taskId != null ? `/workflow/api/tasks/${taskId}/detail` : null,
    fetcher,
  )

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  if (taskId == null) return null

  return (
    <>
      {/* Overlay backdrop (click to close) */}
      <div
        className="fixed inset-0 z-20"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        className="fixed top-0 right-0 z-30 h-full w-[400px] bg-gray-900 border-l border-gray-700 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label="Task detail"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 shrink-0">
          {data ? (
            <div className="flex-1 min-w-0 mr-2">
              <p className="text-[10px] text-gray-500 mb-0.5">#{data.task.id}</p>
              <p className="text-sm font-medium text-gray-100 truncate">{data.task.title}</p>
            </div>
          ) : (
            <p className="text-xs text-gray-500">{error ? 'Error loading task' : 'Loading...'}</p>
          )}
          <button
            onClick={onClose}
            className="shrink-0 text-gray-500 hover:text-gray-300 transition-colors w-6 h-6 flex items-center justify-center rounded hover:bg-gray-800"
            aria-label="Close drawer"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {error && (
            <p className="text-xs text-red-400">Failed to load task details</p>
          )}
          {!data && !error && (
            <p className="text-xs text-gray-600">Loading...</p>
          )}
          {data && (
            <div className="flex flex-col gap-5">
              {/* Badges */}
              <div className="flex flex-wrap gap-1.5">
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${PRIORITY_BADGE[data.task.priority] ?? 'bg-gray-800 text-gray-500'}`}>
                  {data.task.priority}
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${STATUS_BADGE[data.task.status] ?? 'bg-gray-800 text-gray-400'}`}>
                  {data.task.status.replace('_', ' ')}
                </span>
                {data.task.domain && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
                    {data.task.domain}
                  </span>
                )}
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500 border border-gray-700">
                  {data.task.type}
                </span>
              </div>

              {/* Description */}
              {data.task.description && (
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Description</p>
                  <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {data.task.description}
                  </p>
                </div>
              )}

              {/* Meta fields */}
              <div className="grid grid-cols-2 gap-3">
                <Field label="Project">{data.task.project_name}</Field>
                {data.task.pr_number != null && (
                  <Field label="PR">
                    <a
                      href={`https://github.com/search?q=${encodeURIComponent(data.task.branch ?? String(data.task.pr_number))}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 underline"
                    >
                      PR#{data.task.pr_number}
                    </a>
                  </Field>
                )}
                {data.task.branch && (
                  <Field label="Branch">
                    <code className="text-[10px] bg-gray-800 px-1 py-0.5 rounded">{data.task.branch}</code>
                  </Field>
                )}
                <Field label="Created">{formatDate(data.task.created_at)}</Field>
                <Field label="Updated">{formatDate(data.task.updated_at)}</Field>
                {data.task.completed_at && (
                  <Field label="Completed">{formatDate(data.task.completed_at)}</Field>
                )}
              </div>

              {/* Related docs */}
              {data.docs.length > 0 && (
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Related Docs</p>
                  <div className="flex flex-col gap-1">
                    {data.docs.map((doc, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className={`text-[9px] px-1 py-0.5 rounded uppercase ${
                          doc.type === 'spec'
                            ? 'bg-blue-950 text-blue-400 border border-blue-800'
                            : 'bg-gray-800 text-gray-500 border border-gray-700'
                        }`}>
                          {doc.type}
                        </span>
                        <code className="text-[10px] text-gray-400 truncate">{doc.path}</code>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* History timeline */}
              {data.steps.length > 0 && (
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">History</p>
                  <div className="flex flex-col gap-2 border-l border-gray-700 pl-3 ml-1">
                    {data.steps.map((step, i) => (
                      <div key={i} className="relative">
                        <div className="absolute -left-[17px] top-1 w-2 h-2 rounded-full bg-gray-700 border border-gray-600" />
                        <p className="text-xs text-gray-300">{step.label}</p>
                        <p className="text-[10px] text-gray-600">{formatDate(step.timestamp)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes */}
              {data.notes.length > 0 && (
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Notes</p>
                  <div className="flex flex-col gap-2">
                    {data.notes.map((note, i) => (
                      <div key={i} className="bg-gray-800 rounded-lg px-3 py-2 border border-gray-700">
                        <p className="text-xs text-gray-300 leading-relaxed">{note.content}</p>
                        <p className="text-[10px] text-gray-600 mt-1">
                          {note.added_by} · {formatDate(note.created_at)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
