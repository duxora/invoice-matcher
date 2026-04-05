import { useState } from 'react'
import useSWR from 'swr'
import { schedulerApi } from '../lib/api'
import type { Notification } from '../types'

function formatDate(ts?: string | null): string {
  if (!ts) return ''
  return new Date(ts).toLocaleString()
}

export default function NotificationsPage() {
  const [showAll, setShowAll] = useState(false)
  const [marking, setMarking] = useState(false)

  const { data, error, isLoading, mutate } = useSWR<Notification[]>(
    ['scheduler-notifications', showAll],
    () => schedulerApi.getNotifications(showAll),
    { refreshInterval: 15_000 },
  )

  const notifications = data ?? []
  const unreadCount = notifications.filter((n) => !n.read).length

  async function handleMarkRead() {
    setMarking(true)
    try {
      await schedulerApi.markNotificationsRead()
      await mutate()
    } finally {
      setMarking(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-950 text-gray-100">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 shrink-0">
        <button
          onClick={() => setShowAll(false)}
          className={`text-xs px-2.5 py-1 rounded transition-colors ${
            !showAll ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
          }`}
        >
          Unread {!showAll && unreadCount > 0 && <span className="ml-1 text-yellow-400">({unreadCount})</span>}
        </button>
        <button
          onClick={() => setShowAll(true)}
          className={`text-xs px-2.5 py-1 rounded transition-colors ${
            showAll ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
          }`}
        >
          All
        </button>
        <button
          onClick={handleMarkRead}
          disabled={marking || unreadCount === 0}
          className="text-xs ml-auto bg-gray-800 hover:bg-gray-700 text-gray-300 px-2.5 py-1 rounded border border-gray-700 transition-colors disabled:opacity-50"
        >
          {marking ? 'Marking...' : 'Mark all read'}
        </button>
        {error && (
          <span className="text-[10px] text-red-400 bg-red-950 px-1.5 py-0.5 rounded border border-red-800">API error</span>
        )}
      </div>

      {/* Notification list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {isLoading && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">Loading notifications...</span>
          </div>
        )}
        {!isLoading && notifications.length === 0 && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">No notifications</span>
          </div>
        )}
        {!isLoading && notifications.map((n) => (
          <div
            key={n.id}
            className={`px-3 py-2.5 rounded border text-xs ${
              n.read
                ? 'bg-gray-900 border-gray-800 text-gray-400'
                : 'bg-gray-800 border-gray-700 text-gray-200'
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="flex-1">{n.message}</span>
              {!n.read && (
                <span className="shrink-0 h-2 w-2 rounded-full bg-blue-500 mt-1" aria-label="Unread" />
              )}
            </div>
            <div className="mt-1 flex gap-3 text-[10px] text-gray-500">
              {n.task_name && <span>{n.task_name}</span>}
              {n.created_at && <span>{formatDate(n.created_at)}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
