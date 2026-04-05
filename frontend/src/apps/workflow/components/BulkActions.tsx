import { useState } from 'react'
import type { ProjectSummary } from '../types'
import { useSWRConfig } from 'swr'

// ── constants ──────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'backlog', label: 'Backlog' },
  { value: 'done', label: 'Done' },
]

const PRIORITY_OPTIONS = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

// ── main component ─────────────────────────────────────────────────────────

interface BulkActionsProps {
  selectedIds: Set<number>
  projects: ProjectSummary[]
  onClearSelection: () => void
}

export default function BulkActions({ selectedIds, projects, onClearSelection }: BulkActionsProps) {
  const { mutate } = useSWRConfig()
  const [moveProject, setMoveProject] = useState('')
  const [setStatus, setSetStatus] = useState('')
  const [setPriority, setSetPriority] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const count = selectedIds.size
  const ids = Array.from(selectedIds)

  if (count === 0) return null

  async function post(path: string, body: Record<string, unknown>): Promise<void> {
    const res = await fetch(`/workflow/api${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(`API error: ${res.status}`)
  }

  async function handleMove() {
    if (!moveProject) return
    setLoading(true)
    setError(null)
    try {
      await post('/tasks/bulk-move', { task_ids: ids, project_id: moveProject })
      await mutate((key: string) => typeof key === 'string' && key.startsWith('/workflow/api/tasks'))
      onClearSelection()
      setMoveProject('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Move failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleSetStatus() {
    if (!setStatus) return
    setLoading(true)
    setError(null)
    try {
      await post('/tasks/bulk-update', { task_ids: ids, status: setStatus })
      await mutate((key: string) => typeof key === 'string' && key.startsWith('/workflow/api/tasks'))
      onClearSelection()
      setSetStatus('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Status update failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleSetPriority() {
    if (!setPriority) return
    setLoading(true)
    setError(null)
    try {
      await post('/tasks/bulk-update', { task_ids: ids, priority: setPriority })
      await mutate((key: string) => typeof key === 'string' && key.startsWith('/workflow/api/tasks'))
      onClearSelection()
      setSetPriority('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Priority update failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-gray-900 border-t border-gray-700 px-4 py-2.5 flex items-center gap-3 flex-wrap shadow-lg">
      {/* Count */}
      <span className="text-xs font-medium text-gray-300 shrink-0">
        {count} selected
      </span>

      <div className="w-px h-4 bg-gray-700 shrink-0" />

      {/* Move to project */}
      <div className="flex items-center gap-1.5">
        <select
          value={moveProject}
          onChange={(e) => setMoveProject(e.target.value)}
          disabled={loading}
          className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300 disabled:opacity-50"
          aria-label="Move to project"
        >
          <option value="">Move to project...</option>
          {projects.map((p) => (
            <option key={p.project_id} value={p.project_id}>
              {p.project_name}
            </option>
          ))}
        </select>
        <button
          onClick={handleMove}
          disabled={!moveProject || loading}
          className="text-xs px-2 py-1 bg-gray-800 border border-gray-700 rounded text-gray-300 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Move
        </button>
      </div>

      <div className="w-px h-4 bg-gray-700 shrink-0" />

      {/* Set status */}
      <div className="flex items-center gap-1.5">
        <select
          value={setStatus}
          onChange={(e) => setSetStatus(e.target.value)}
          disabled={loading}
          className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300 disabled:opacity-50"
          aria-label="Set status"
        >
          <option value="">Set status...</option>
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          onClick={handleSetStatus}
          disabled={!setStatus || loading}
          className="text-xs px-2 py-1 bg-gray-800 border border-gray-700 rounded text-gray-300 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Apply
        </button>
      </div>

      <div className="w-px h-4 bg-gray-700 shrink-0" />

      {/* Set priority */}
      <div className="flex items-center gap-1.5">
        <select
          value={setPriority}
          onChange={(e) => setSetPriority(e.target.value)}
          disabled={loading}
          className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300 disabled:opacity-50"
          aria-label="Set priority"
        >
          <option value="">Set priority...</option>
          {PRIORITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          onClick={handleSetPriority}
          disabled={!setPriority || loading}
          className="text-xs px-2 py-1 bg-gray-800 border border-gray-700 rounded text-gray-300 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Apply
        </button>
      </div>

      {error && (
        <span className="text-[10px] text-red-400 ml-1">{error}</span>
      )}

      <div className="ml-auto">
        <button
          onClick={onClearSelection}
          disabled={loading}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-50"
        >
          Clear selection
        </button>
      </div>
    </div>
  )
}
