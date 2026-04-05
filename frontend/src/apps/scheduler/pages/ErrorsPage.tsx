import { useState } from 'react'
import useSWR from 'swr'
import { schedulerApi } from '../lib/api'
import { useSchedulerTasks } from '../hooks/useSchedulerTasks'
import type { ErrorRecord } from '../types'

function formatDate(ts: string | null): string {
  if (!ts) return '—'
  return new Date(ts).toLocaleString()
}

export default function ErrorsPage() {
  const [taskFilter, setTaskFilter] = useState('')
  const { tasks } = useSchedulerTasks()

  const { data, error, isLoading } = useSWR<ErrorRecord[]>(
    ['scheduler-errors', taskFilter],
    () => schedulerApi.getErrors(taskFilter || undefined),
    { refreshInterval: 15_000 },
  )

  const errors = data ?? []

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
        <span className="text-[10px] text-gray-600 ml-auto">
          {isLoading ? 'Loading...' : `${errors.length} error${errors.length !== 1 ? 's' : ''}`}
        </span>
        {error && (
          <span className="text-[10px] text-red-400 bg-red-950 px-1.5 py-0.5 rounded border border-red-800">API error</span>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {isLoading && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">Loading errors...</span>
          </div>
        )}
        {!isLoading && errors.length === 0 && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">No errors found</span>
          </div>
        )}
        {!isLoading && errors.length > 0 && (
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left py-1.5 pr-4 font-medium w-32">Task</th>
                <th className="text-left py-1.5 pr-4 font-medium">Message</th>
                <th className="text-left py-1.5 font-medium w-40">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {errors.map((err, i) => (
                <tr key={i} className="border-b border-gray-900 hover:bg-gray-900/40">
                  <td className="py-2 pr-4 text-gray-300 align-top">{err.task_name}</td>
                  <td className="py-2 pr-4 text-red-300 font-mono break-all">{err.message}</td>
                  <td className="py-2 text-gray-500 align-top whitespace-nowrap">{formatDate(err.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
