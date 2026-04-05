import type { Session, DetailTarget } from '../types'
import SessionCard from './SessionCard'

interface SessionSidebarProps {
  sessions: Session[]
  onSelect: (target: DetailTarget) => void
}

export default function SessionSidebar({ sessions, onSelect }: SessionSidebarProps) {
  const alive = sessions.filter((s) => s.alive)
  const dead = sessions.filter((s) => !s.alive)

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider px-2 mb-2">
        Sessions
        {alive.length > 0 && (
          <span className="ml-2 px-1.5 py-0.5 bg-emerald-900/50 text-emerald-400 rounded text-[10px]">
            {alive.length}
          </span>
        )}
      </h2>
      {sessions.length === 0 ? (
        <p className="text-xs text-gray-600 px-2">No sessions running</p>
      ) : (
        <div className="flex flex-col gap-1">
          {alive.map((s) => (
            <SessionCard key={s.sessionId} session={s} onSelect={onSelect} />
          ))}
          {dead.map((s) => (
            <SessionCard key={s.sessionId} session={s} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  )
}
