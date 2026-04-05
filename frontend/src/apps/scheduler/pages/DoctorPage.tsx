import useSWR from 'swr'
import { schedulerApi } from '../lib/api'
import type { HealthCheck } from '../types'

export default function DoctorPage() {
  const { data, error, isLoading, mutate } = useSWR<HealthCheck[]>(
    'scheduler-doctor',
    () => schedulerApi.getDoctor(),
    { refreshInterval: 30_000 },
  )

  const checks = data ?? []
  const allOk = checks.length > 0 && checks.every((c) => c.ok)

  return (
    <div className="flex flex-col h-full bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 shrink-0">
        <span className="text-xs font-medium text-gray-300">Health Checks</span>
        {!isLoading && checks.length > 0 && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${
            allOk ? 'text-green-400 bg-green-950 border-green-800' : 'text-red-400 bg-red-950 border-red-800'
          }`}>
            {allOk ? 'All healthy' : `${checks.filter((c) => !c.ok).length} issue(s)`}
          </span>
        )}
        <button
          onClick={() => mutate()}
          className="ml-auto text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-2.5 py-1 rounded border border-gray-700 transition-colors"
        >
          Refresh
        </button>
        {error && (
          <span className="text-[10px] text-red-400 bg-red-950 px-1.5 py-0.5 rounded border border-red-800">API error</span>
        )}
      </div>

      {/* Checks list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {isLoading && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">Running health checks...</span>
          </div>
        )}
        {!isLoading && checks.length === 0 && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">No checks available</span>
          </div>
        )}
        {!isLoading && checks.map((check) => (
          <div
            key={check.name}
            className={`flex items-start gap-3 px-3 py-2.5 rounded border ${
              check.ok ? 'bg-gray-900 border-gray-800' : 'bg-red-950/30 border-red-900'
            }`}
          >
            <span
              className={`shrink-0 mt-0.5 text-base ${check.ok ? 'text-green-400' : 'text-red-400'}`}
              aria-hidden="true"
            >
              {check.ok ? '✓' : '✗'}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-gray-200">{check.name}</div>
              {check.detail && (
                <div className="text-[11px] text-gray-400 mt-0.5">{check.detail}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
