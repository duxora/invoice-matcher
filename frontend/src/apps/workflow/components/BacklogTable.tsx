import type { Task, DetailTarget } from '../types'

interface BacklogTableProps {
  tasks: Task[]
  onSelect: (target: DetailTarget) => void
}

const priorityColor: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-gray-400',
}

export default function BacklogTable({ tasks, onSelect }: BacklogTableProps) {
  if (tasks.length === 0) return null

  return (
    <div>
      <h2 className="text-xs font-medium text-gray-300 uppercase tracking-wider mb-2">
        Backlog
        <span className="ml-2 text-gray-500">({tasks.length})</span>
      </h2>
      <div className="flex flex-col gap-0.5">
        {tasks.map((task) => (
          <button
            key={task.id}
            onClick={() => onSelect({ kind: 'task', task })}
            className="w-full text-left flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-900 transition-colors"
          >
            <span className="text-xs text-gray-400">#{task.id}</span>
            <span className="text-sm text-gray-200 truncate flex-1">{task.title}</span>
            <span className={`text-[11px] ${priorityColor[task.priority] ?? 'text-gray-400'}`}>
              {task.priority}
            </span>
            <span className="text-[11px] text-gray-400">{task.type}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
