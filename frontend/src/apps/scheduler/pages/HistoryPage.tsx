import { useState } from 'react'
import useSWR from 'swr'
import { schedulerApi } from '../lib/api'
import { useSchedulerTasks } from '../hooks/useSchedulerTasks'
import type { RunRecord } from '../types'

function statusColor(status: string): string {
  if (status === 'success') return 'text-green-400 bg-green-950 border-green-800'
  if (status === 'failed' || status === 'timeout') return 'text-red-400 bg-red-950 border-red-800'
  if (status === 'running') return 'text-yellow-400 bg-yellow-950 border-yellow-800'
  return 'text-gray-400 bg-gray-900 border-gray-700'
}

function formatDate(ts: string | null): string {
  if (!ts) return '—'
  return new Date(ts).toLocaleString()
}

function formatDuration(s: number | null): string {
  if (s === null) return '—'
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

const LIMIT_OPTIONS = [20, 50, 100, 200]

export default function HistoryPage() {
  const [taskFilter, setTaskFilter] = useState('')
  const [limit, setLimit] = useState(50)
  const { tasks } = useSchedulerTasks()

  const { data, error, isLoading } = useSWR<RunRecord[]>(
    ['scheduler-history', taskFilter, limit],
    () => schedulerApi.getHistory({ task: taskFilter || undefined, n: limit }),
    { refreshInterval: 15_000 },
  )

  const runs = data ?? []

  return (
    <div className="flex flex-col h-full bg-gray-950 text-gray-100">
      {/* Filter bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 shrink-0">
        <select
          value={taskFilter}
          onChange={(e) => setTaskFilter(e.target.value)}
          className="text-xs bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300"
          aria-label="Filter by task"
        >
          <option value="">All tasks</option>
          {tasks.map((t) => (
            <option key={t.slug} value={t.name}>{t.name}</option>
          ))}
        </select>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="text-xs bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300"
          aria-label="Result limit"
        >
          {LIMIT_OPTIONS.map((n) => (
            <option key={n} value={n}>{n} runs</option>
          ))}
        </select>
        <span className="text-[10px] text-gray-600 ml-auto">
          {isLoading ? 'Loading...' : `${runs.length} run${runs.length !== 1 ? 's' : ''}`}
        </span>
        {error && (
          <span className="text-[10px] text-red-400 bg-red-950 px-1.5 py-0.5 rounded border border-red-800">API error</span>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {isLoading && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">Loading history...</span>
          </div>
        )}
        {!isLoading && runs.length === 0 && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">No history found</span>
          </div>
        )}
        {!isLoading && runs.length > 0 && (
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left py-1.5 pr-4 font-medium">Task</th>
                <th className="text-left py-1.5 pr-4 font-medium">Status</th>
                <th className="text-left py-1.5 pr-4 font-medium">Started</th>
                <th className="text-left py-1.5 pr-4 font-medium">Finished</th>
                <th className="text-left py-1.5 pr-4 font-medium">Duration</th>
                <th className="text-left py-1.5 font-medium">Cost</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-b border-gray-900 hover:bg-gray-900/40">
                  <td className="py-2 pr-4 text-gray-300">{run.task_name}</td>
                  <td className="py-2 pr-4">
                    <span className={`px-1.5 py-0.5 rounded border text-[10px] font-medium ${statusColor(run.status)}`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-gray-400">{formatDate(run.started_at)}</td>
                  <td className="py-2 pr-4 text-gray-400">{formatDate(run.finished_at)}</td>
                  <td className="py-2 pr-4 text-gray-400">{formatDuration(run.duration_seconds)}</td>
                  <td className="py-2 text-gray-400">
                    {run.cost_usd > 0 ? `$${run.cost_usd.toFixed(4)}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
