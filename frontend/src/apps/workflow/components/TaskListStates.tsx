import { ClipboardIcon, ErrorCircleIcon } from './ui/icons'

// ── Empty state ─────────────────────────────────────────────────────────────

interface EmptyStateProps {
  search: string
  phaseFilter: string
}

export function EmptyState({ search, phaseFilter }: EmptyStateProps) {
  const filtered = search.trim() || phaseFilter
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3 text-center px-4">
      <div className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center">
        <ClipboardIcon className="text-slate-500" />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-400">
          {filtered ? 'No matching tasks' : 'No tasks'}
        </p>
        <p className="text-xs text-slate-600 mt-0.5">
          {filtered ? 'Try adjusting your filters' : 'Tasks will appear here when created'}
        </p>
      </div>
    </div>
  )
}

// ── Loading skeleton ────────────────────────────────────────────────────────

export function LoadingState() {
  return (
    <div className="flex flex-col gap-1.5 p-2 animate-pulse">
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className="h-14 rounded-lg bg-slate-800/50 border-l-2 border-slate-700/30"
          style={{ opacity: 1 - i * 0.15 }}
        />
      ))}
    </div>
  )
}

// ── Error state ─────────────────────────────────────────────────────────────

export function ErrorState({ message = 'Failed to load tasks' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3">
      <div className="w-10 h-10 rounded-full bg-red-900/30 border border-red-800/50 flex items-center justify-center">
        <ErrorCircleIcon className="text-red-400" />
      </div>
      <p className="text-sm text-red-300 font-medium">{message}</p>
    </div>
  )
}
