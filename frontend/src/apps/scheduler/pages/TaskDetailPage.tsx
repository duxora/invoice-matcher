import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import useSWR from 'swr'
import { schedulerApi } from '../lib/api'
import type { TaskDetailResponse, LogResponse } from '../types'

function statusColor(status?: string | null): string {
  if (!status) return 'text-gray-400 bg-gray-900 border-gray-700'
  if (status === 'success') return 'text-green-400 bg-green-950 border-green-800'
  if (status === 'failed' || status === 'timeout') return 'text-red-400 bg-red-950 border-red-800'
  if (status === 'running' || status === 'pending') return 'text-yellow-400 bg-yellow-950 border-yellow-800'
  return 'text-gray-400 bg-gray-900 border-gray-700'
}

function formatDate(ts: string | null | undefined): string {
  if (!ts) return '—'
  return new Date(ts).toLocaleString()
}

function formatDuration(s: number | null): string {
  if (s === null) return '—'
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

export default function TaskDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [editingPrompt, setEditingPrompt] = useState(false)
  const [promptValue, setPromptValue] = useState('')
  const [savingPrompt, setSavingPrompt] = useState(false)
  const [showLog, setShowLog] = useState(false)

  const { data, error, isLoading, mutate } = useSWR<TaskDetailResponse>(
    slug ? `scheduler-task-${slug}` : null,
    () => schedulerApi.getTask(slug!),
    { refreshInterval: 15_000 },
  )

  const { data: logData, isLoading: logLoading } = useSWR<LogResponse>(
    showLog && slug ? `scheduler-log-${slug}` : null,
    () => schedulerApi.getLogs(slug!),
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-950">
        <span className="text-xs text-gray-600">Loading task...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-950 gap-3">
        <span className="text-xs text-red-400">Failed to load task</span>
        <button
          onClick={() => navigate('/scheduler')}
          className="text-xs text-blue-400 hover:underline"
        >
          Back to dashboard
        </button>
      </div>
    )
  }

  const { task, runs, errors } = data

  async function handleSavePrompt() {
    if (!slug) return
    setSavingPrompt(true)
    try {
      await schedulerApi.updatePrompt(slug, promptValue)
      await mutate()
      setEditingPrompt(false)
    } finally {
      setSavingPrompt(false)
    }
  }

  function startEditingPrompt() {
    setPromptValue(task.prompt)
    setEditingPrompt(true)
  }

  return (
    <div className="flex flex-col h-full bg-gray-950 text-gray-100 overflow-y-auto">
      {/* Back + header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-800 shrink-0">
        <button
          onClick={() => navigate('/scheduler')}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          ← Back
        </button>
        <span className="text-gray-700">/</span>
        <h1 className="text-sm font-medium text-gray-200">{task.name}</h1>
        <span className={`ml-1 px-1.5 py-0.5 rounded border text-[10px] font-medium ${statusColor(task.last_status)}`}>
          {task.last_status ?? 'unknown'}
        </span>
      </div>

      <div className="flex-1 px-4 py-4 space-y-6 overflow-y-auto">
        {/* Metadata */}
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Metadata</h2>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
            {[
              { label: 'Schedule', value: task.schedule },
              { label: 'Model', value: task.model },
              { label: 'Max turns', value: task.max_turns },
              { label: 'Timeout', value: `${task.timeout}s` },
              { label: 'Tools', value: Array.isArray(task.tools) ? task.tools.join(', ') : task.tools },
              { label: 'Workdir', value: task.workdir || '—' },
              { label: 'Enabled', value: task.enabled ? 'Yes' : 'No' },
              { label: 'Last run', value: formatDate(task.last_run_at) },
              { label: 'Next run', value: formatDate(task.next_run_at) },
              { label: 'Run count', value: task.run_count ?? 0 },
            ].map(({ label, value }) => (
              <div key={label} className="flex gap-2">
                <span className="text-gray-500 w-20 shrink-0">{label}</span>
                <span className="text-gray-300 font-mono">{String(value)}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Prompt */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Prompt</h2>
            {!editingPrompt && (
              <button
                onClick={startEditingPrompt}
                className="text-[10px] bg-gray-800 hover:bg-gray-700 text-gray-300 px-2 py-0.5 rounded border border-gray-700 transition-colors"
              >
                Edit
              </button>
            )}
          </div>
          {editingPrompt ? (
            <div className="space-y-2">
              <textarea
                value={promptValue}
                onChange={(e) => setPromptValue(e.target.value)}
                rows={10}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-xs font-mono text-gray-200 focus:border-blue-600 focus:outline-none resize-y"
                aria-label="Task prompt"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSavePrompt}
                  disabled={savingPrompt}
                  className="text-xs bg-blue-700 hover:bg-blue-600 text-white px-3 py-1 rounded transition-colors disabled:opacity-50"
                >
                  {savingPrompt ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={() => setEditingPrompt(false)}
                  className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1 rounded border border-gray-700 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <pre className="text-xs font-mono bg-gray-900 border border-gray-800 rounded p-3 overflow-x-auto whitespace-pre-wrap text-gray-300 max-h-48 overflow-y-auto">
              {task.prompt || '(no prompt)'}
            </pre>
          )}
        </section>

        {/* Recent runs */}
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Recent Runs ({runs.length})
          </h2>
          {runs.length === 0 ? (
            <p className="text-xs text-gray-600">No runs yet</p>
          ) : (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left py-1.5 pr-4 font-medium">Status</th>
                  <th className="text-left py-1.5 pr-4 font-medium">Started</th>
                  <th className="text-left py-1.5 pr-4 font-medium">Duration</th>
                  <th className="text-left py-1.5 font-medium">Cost</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-gray-900 hover:bg-gray-900/40">
                    <td className="py-1.5 pr-4">
                      <span className={`px-1.5 py-0.5 rounded border text-[10px] font-medium ${statusColor(run.status)}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="py-1.5 pr-4 text-gray-400">{formatDate(run.started_at)}</td>
                    <td className="py-1.5 pr-4 text-gray-400">{formatDuration(run.duration_seconds)}</td>
                    <td className="py-1.5 text-gray-400">
                      {run.cost_usd > 0 ? `$${run.cost_usd.toFixed(4)}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {/* Recent errors */}
        {errors.length > 0 && (
          <section>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Recent Errors ({errors.length})
            </h2>
            <div className="space-y-1.5">
              {errors.map((err, i) => (
                <div key={i} className="bg-red-950/30 border border-red-900 rounded px-3 py-2">
                  <p className="text-xs text-red-300 font-mono break-all">{err.message}</p>
                  {err.timestamp && (
                    <p className="text-[10px] text-red-500 mt-0.5">{formatDate(err.timestamp)}</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Log */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Log</h2>
            <button
              onClick={() => setShowLog((v) => !v)}
              className="text-[10px] bg-gray-800 hover:bg-gray-700 text-gray-300 px-2 py-0.5 rounded border border-gray-700 transition-colors"
            >
              {showLog ? 'Hide log' : 'View log'}
            </button>
          </div>
          {showLog && (
            <div>
              {logLoading ? (
                <p className="text-xs text-gray-600">Loading log...</p>
              ) : logData ? (
                <div>
                  {logData.log_file && (
                    <p className="text-[10px] text-gray-500 mb-1 font-mono">{logData.log_file}</p>
                  )}
                  <pre className="text-[11px] font-mono bg-gray-900 border border-gray-800 rounded p-3 overflow-x-auto whitespace-pre text-gray-300 max-h-80 overflow-y-auto">
                    {logData.content || '(empty log)'}
                  </pre>
                </div>
              ) : (
                <p className="text-xs text-gray-600">No log available</p>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
