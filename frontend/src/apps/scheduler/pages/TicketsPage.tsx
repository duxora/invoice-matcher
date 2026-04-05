import { useState } from 'react'
import useSWR from 'swr'
import { schedulerApi } from '../lib/api'
import type { Ticket } from '../types'

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'open', label: 'Open' },
  { value: 'resolved', label: 'Resolved' },
]

function statusColor(status: string): string {
  if (status === 'open') return 'text-yellow-400 bg-yellow-950 border-yellow-800'
  if (status === 'resolved') return 'text-green-400 bg-green-950 border-green-800'
  return 'text-gray-400 bg-gray-900 border-gray-700'
}

export default function TicketsPage() {
  const [statusFilter, setStatusFilter] = useState('open')
  const [resolving, setResolving] = useState<Set<number>>(new Set())

  const { data, error, isLoading, mutate } = useSWR<Ticket[]>(
    ['scheduler-tickets', statusFilter],
    () => schedulerApi.getTickets(statusFilter || undefined),
    { refreshInterval: 15_000 },
  )

  const tickets = data ?? []

  async function handleResolve(id: number) {
    setResolving((prev) => new Set(prev).add(id))
    try {
      await schedulerApi.resolveTicket(id)
      await mutate()
    } finally {
      setResolving((prev) => { const s = new Set(prev); s.delete(id); return s })
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-950 text-gray-100">
      {/* Filter bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 shrink-0">
        {STATUS_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setStatusFilter(value)}
            className={`text-xs px-2.5 py-1 rounded transition-colors ${
              statusFilter === value
                ? 'bg-gray-700 text-white'
                : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
            }`}
          >
            {label}
          </button>
        ))}
        <span className="text-[10px] text-gray-600 ml-auto">
          {isLoading ? 'Loading...' : `${tickets.length} ticket${tickets.length !== 1 ? 's' : ''}`}
        </span>
        {error && (
          <span className="text-[10px] text-red-400 bg-red-950 px-1.5 py-0.5 rounded border border-red-800">API error</span>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {isLoading && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">Loading tickets...</span>
          </div>
        )}
        {!isLoading && tickets.length === 0 && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">No tickets found</span>
          </div>
        )}
        {!isLoading && tickets.length > 0 && (
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left py-1.5 pr-4 font-medium">Task</th>
                <th className="text-left py-1.5 pr-4 font-medium">Message</th>
                <th className="text-left py-1.5 pr-4 font-medium">Status</th>
                <th className="text-left py-1.5 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr key={ticket.id} className="border-b border-gray-900 hover:bg-gray-900/40">
                  <td className="py-2 pr-4 text-gray-300 align-top">{ticket.task_name}</td>
                  <td className="py-2 pr-4 text-gray-300 break-all">{ticket.message}</td>
                  <td className="py-2 pr-4 align-top">
                    <span className={`px-1.5 py-0.5 rounded border text-[10px] font-medium ${statusColor(ticket.status)}`}>
                      {ticket.status}
                    </span>
                  </td>
                  <td className="py-2 align-top">
                    {ticket.status === 'open' && (
                      <button
                        onClick={() => handleResolve(ticket.id)}
                        disabled={resolving.has(ticket.id)}
                        className="text-[10px] bg-green-800 hover:bg-green-700 text-green-100 px-2 py-0.5 rounded transition-colors disabled:opacity-50"
                      >
                        {resolving.has(ticket.id) ? 'Resolving...' : 'Resolve'}
                      </button>
                    )}
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
