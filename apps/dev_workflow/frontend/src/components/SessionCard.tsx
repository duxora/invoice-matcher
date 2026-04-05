import type { Session, DetailTarget } from '../types'
import { formatTimeAgo, formatElapsed } from '../lib/time'

interface SessionCardProps {
  session: Session
  onSelect: (target: DetailTarget) => void
}

export default function SessionCard({ session, onSelect }: SessionCardProps) {
  const heartbeatAge = formatTimeAgo(session.heartbeat_at)
  const isAlive = session.alive

  return (
    <button
      onClick={() => onSelect({ kind: 'session', session })}
      className="w-full text-left p-2 rounded-md hover:bg-gray-800 transition-colors"
    >
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isAlive ? 'bg-emerald-500' : 'bg-gray-600'}`} />
        <span className="text-xs text-gray-300 truncate">
          {session.name ?? `Session ${session.sessionId.slice(0, 6)}`}
        </span>
      </div>
      {session.task_id != null && (
        <p className="text-[10px] text-gray-500 mt-0.5 ml-4">
          Task #{session.task_id}
        </p>
      )}
      <div className="flex items-center gap-2 mt-0.5 ml-4 text-[10px] text-gray-600">
        <span>⏱ {formatElapsed(session.startedAt)}</span>
        {session.heartbeat_at && <span>♥ {heartbeatAge}</span>}
      </div>
    </button>
  )
}
