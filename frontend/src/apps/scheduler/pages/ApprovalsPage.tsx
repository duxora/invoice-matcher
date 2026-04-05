import { useState } from 'react'
import useSWR from 'swr'
import { schedulerApi } from '../lib/api'
import type { Approval } from '../types'

function formatDate(ts?: string | null): string {
  if (!ts) return ''
  return new Date(ts).toLocaleString()
}

export default function ApprovalsPage() {
  const [busy, setBusy] = useState<Set<string>>(new Set())

  const { data, error, isLoading, mutate } = useSWR<Approval[]>(
    'scheduler-approvals',
    () => schedulerApi.getApprovals(),
    { refreshInterval: 10_000 },
  )

  const approvals = data ?? []
  const pending = approvals.filter((a) => a.status === 'pending')

  async function handleAction(id: number, action: 'approve' | 'reject') {
    const key = `${action}-${id}`
    setBusy((prev) => new Set(prev).add(key))
    try {
      if (action === 'approve') {
        await schedulerApi.approveApproval(id)
      } else {
        await schedulerApi.rejectApproval(id)
      }
      await mutate()
    } finally {
      setBusy((prev) => { const s = new Set(prev); s.delete(key); return s })
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 shrink-0">
        <span className="text-xs text-gray-500">
          {isLoading ? 'Loading...' : `${pending.length} pending approval${pending.length !== 1 ? 's' : ''}`}
        </span>
        {error && (
          <span className="text-[10px] text-red-400 bg-red-950 px-1.5 py-0.5 rounded border border-red-800">API error</span>
        )}
      </div>

      {/* Approvals list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {isLoading && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">Loading approvals...</span>
          </div>
        )}
        {!isLoading && pending.length === 0 && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">No pending approvals</span>
          </div>
        )}
        {!isLoading && pending.map((approval) => (
          <div key={approval.id} className="bg-gray-900 border border-gray-800 rounded p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-gray-200">{approval.task_name}</div>
                {approval.created_at && (
                  <div className="text-[10px] text-gray-500 mt-0.5">{formatDate(approval.created_at)}</div>
                )}
              </div>
              <div className="flex gap-1.5 shrink-0">
                <button
                  onClick={() => handleAction(approval.id, 'approve')}
                  disabled={busy.has(`approve-${approval.id}`) || busy.has(`reject-${approval.id}`)}
                  className="text-[10px] bg-green-800 hover:bg-green-700 text-green-100 px-2 py-0.5 rounded transition-colors disabled:opacity-50"
                >
                  {busy.has(`approve-${approval.id}`) ? 'Approving...' : 'Approve'}
                </button>
                <button
                  onClick={() => handleAction(approval.id, 'reject')}
                  disabled={busy.has(`approve-${approval.id}`) || busy.has(`reject-${approval.id}`)}
                  className="text-[10px] bg-red-900 hover:bg-red-800 text-red-100 px-2 py-0.5 rounded transition-colors disabled:opacity-50"
                >
                  {busy.has(`reject-${approval.id}`) ? 'Rejecting...' : 'Reject'}
                </button>
              </div>
            </div>

            {/* Artifact content */}
            {approval.artifact && (
              <div className="mt-2">
                {approval.artifact.content_type && (
                  <div className="text-[10px] text-gray-500 mb-1">{approval.artifact.content_type}</div>
                )}
                <pre className="text-[11px] font-mono bg-gray-950 border border-gray-800 rounded p-2 overflow-x-auto whitespace-pre-wrap text-gray-300 max-h-48 overflow-y-auto">
                  {approval.artifact.content}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
