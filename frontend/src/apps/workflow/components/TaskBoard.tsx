import { useState, useMemo, useCallback } from 'react'
import type { Task } from '../types'
import { useTaskBoard } from '../hooks/useTaskBoard'
import TaskDetailDrawer from './TaskDetailDrawer'
import BulkActions from './BulkActions'
import DomainMapModal from './DomainMapModal'
import MisplacedBanner from './MisplacedBanner'

// ── constants ──────────────────────────────────────────────────────────────

const PHASES = [
  { key: 'intake', label: 'Intake', color: 'text-blue-300 bg-blue-900/60 border-blue-700' },
  { key: 'backlog', label: 'Backlog', color: 'text-indigo-300 bg-indigo-900/60 border-indigo-700' },
  { key: 'implement', label: 'Implement', color: 'text-emerald-300 bg-emerald-900/60 border-emerald-700' },
  { key: 'pr_ci', label: 'PR / CI', color: 'text-amber-300 bg-amber-900/60 border-amber-700' },
  { key: 'review', label: 'Review', color: 'text-orange-300 bg-orange-900/60 border-orange-700' },
  { key: 'deploy', label: 'Deploy', color: 'text-purple-300 bg-purple-900/60 border-purple-700' },
  { key: 'verify', label: 'Verify', color: 'text-teal-300 bg-teal-900/60 border-teal-700' },
  { key: 'close', label: 'Close', color: 'text-gray-400 bg-gray-700/60 border-gray-600' },
] as const

type PhaseKey = (typeof PHASES)[number]['key']

const PRIORITY_BADGE: Record<string, string> = {
  critical: 'bg-red-900/80 text-red-200 border border-red-600',
  high: 'bg-orange-900/80 text-orange-200 border border-orange-600',
  medium: 'bg-yellow-900/80 text-yellow-200 border border-yellow-600',
  low: 'bg-gray-700/80 text-gray-400 border border-gray-600',
}

const PRIORITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

const STATUS_BADGE: Record<string, string> = {
  open: 'bg-blue-900/80 text-blue-200 border border-blue-600',
  in_progress: 'bg-amber-900/80 text-amber-200 border border-amber-600',
  backlog: 'bg-indigo-900/80 text-indigo-200 border border-indigo-600',
  done: 'bg-emerald-900/80 text-emerald-200 border border-emerald-600',
}

const STATUS_OPTIONS = [
  { value: '', label: 'Active (no done)' },
  { value: 'open', label: 'Open only' },
  { value: 'in_progress', label: 'In Progress only' },
  { value: 'done', label: 'Done only' },
  { value: 'all', label: 'All statuses' },
]

// ── sub-components ─────────────────────────────────────────────────────────

interface ProjectCardProps {
  label: string
  open: number
  inProgress: number
  done: number
  active: boolean
  onClick: () => void
}

function ProjectCard({ label, open, inProgress, done, active, onClick }: ProjectCardProps) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col gap-1.5 px-3.5 py-2.5 rounded-lg border transition-all text-left ${
        active
          ? 'bg-slate-700/80 border-blue-400 shadow-sm shadow-blue-500/10'
          : 'bg-slate-800/60 border-slate-600/80 hover:border-slate-500 hover:bg-slate-700/50'
      }`}
    >
      <span className="text-xs font-semibold text-slate-100 truncate max-w-[140px]">{label}</span>
      <div className="flex items-center gap-2.5">
        <span className="text-[11px] text-blue-300 font-medium">{open} open</span>
        <span className="text-[11px] text-amber-300 font-medium">{inProgress} in prog</span>
        <span className="text-[11px] text-emerald-300 font-medium">{done} done</span>
      </div>
    </button>
  )
}

interface PhaseChipProps {
  phase: (typeof PHASES)[number]
  count: number
  active: boolean
  onClick: () => void
}

function PhaseChip({ phase, count, active, onClick }: PhaseChipProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] font-medium transition-all ${phase.color} ${
        active ? 'ring-1 ring-blue-400 shadow-sm' : 'opacity-75 hover:opacity-100'
      }`}
    >
      <span>{phase.label}</span>
      {count > 0 && (
        <span className="bg-white/10 px-1.5 rounded text-[10px] font-semibold">{count}</span>
      )}
    </button>
  )
}

interface TaskRowProps {
  task: Task
  selected: boolean
  onSelect: (id: number, checked: boolean) => void
  onOpenDetail: (id: number) => void
}

function TaskRow({ task, selected, onSelect, onOpenDetail }: TaskRowProps) {
  return (
    <div
      className={`px-3 py-2.5 rounded-lg border transition-all ${
        selected
          ? 'bg-slate-700/60 border-slate-500'
          : 'border-transparent hover:bg-slate-800/60 hover:border-slate-700'
      }`}
    >
      <div className="flex items-start gap-2.5">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={selected}
          onChange={(e) => onSelect(task.id, e.target.checked)}
          onClick={(e) => e.stopPropagation()}
          className="shrink-0 accent-blue-400 cursor-pointer mt-0.5"
          aria-label={`Select task #${task.id}`}
        />

        {/* ID */}
        <span className="text-[11px] text-slate-400 shrink-0 mt-0.5 font-mono">#{task.id}</span>

        {/* Content area */}
        <div className="flex-1 min-w-0">
          {/* Title row */}
          <button
            className="text-[13px] text-slate-200 text-left hover:text-white transition-colors line-clamp-2 md:line-clamp-1 w-full leading-snug"
            onClick={() => onOpenDetail(task.id)}
          >
            {task.title}
          </button>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded-md font-medium ${PRIORITY_BADGE[task.priority] ?? 'bg-gray-700 text-gray-400'}`}
            >
              {task.priority}
            </span>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded-md font-medium ${STATUS_BADGE[task.status] ?? 'bg-gray-700 text-gray-400'}`}
            >
              {task.status.replace('_', ' ')}
            </span>
            <span className="text-[11px] text-slate-400 truncate max-w-[140px]">
              {task.project_name ?? task.project_id}
            </span>
            {task.domain && (
              <span className="text-[10px] text-slate-300 bg-slate-700/80 px-1.5 py-0.5 rounded-md border border-slate-600">
                {task.domain}
              </span>
            )}
            {task.pr_number != null && (
              <a
                href={`https://github.com/search?q=${encodeURIComponent(task.branch ?? String(task.pr_number))}`}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-[11px] text-blue-300 hover:text-blue-200 font-medium"
              >
                PR#{task.pr_number}
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── main component ─────────────────────────────────────────────────────────

export default function TaskBoard() {
  const [projectFilter, setProjectFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [phaseFilter, setPhaseFilter] = useState<PhaseKey | ''>('')
  const [search, setSearch] = useState('')

  // Task detail drawer
  const [drawerTaskId, setDrawerTaskId] = useState<number | null>(null)

  // Bulk selection
  const [selectedTasks, setSelectedTasks] = useState<Set<number>>(new Set())

  // Domain map modal
  const [domainMapOpen, setDomainMapOpen] = useState(false)

  const { tasks, projects, tasksError, projectsError } = useTaskBoard(projectFilter, statusFilter)

  // Aggregate counts for "All" project card
  const allCounts = useMemo(() => {
    if (!projects) return { open: 0, inProgress: 0, done: 0 }
    return projects.reduce(
      (acc, p) => ({
        open: acc.open + p.open_count,
        inProgress: acc.inProgress + p.in_progress_count,
        done: acc.done + p.done_count,
      }),
      { open: 0, inProgress: 0, done: 0 },
    )
  }, [projects])

  // Phase counts from current task list
  const phaseCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of tasks ?? []) {
      counts[t.phase] = (counts[t.phase] ?? 0) + 1
    }
    return counts
  }, [tasks])

  // Client-side filtering: search + phase, sorted by priority (high → low)
  const visibleTasks = useMemo(() => {
    let result = tasks ?? []
    if (phaseFilter) {
      result = result.filter((t) => t.phase === phaseFilter)
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      result = result.filter(
        (t) => String(t.id).includes(q) || t.title.toLowerCase().includes(q),
      )
    }
    return [...result].sort(
      (a, b) => (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9),
    )
  }, [tasks, phaseFilter, search])

  const handleProjectClick = (projectId: string) => {
    setProjectFilter((prev) => (prev === projectId ? '' : projectId))
  }

  const handlePhaseClick = (phase: PhaseKey) => {
    setPhaseFilter((prev) => (prev === phase ? '' : phase))
  }

  // Checkbox handlers
  const handleSelectTask = useCallback((id: number, checked: boolean) => {
    setSelectedTasks((prev) => {
      const next = new Set(prev)
      if (checked) {
        next.add(id)
      } else {
        next.delete(id)
      }
      return next
    })
  }, [])

  const allVisibleSelected =
    visibleTasks.length > 0 && visibleTasks.every((t) => selectedTasks.has(t.id))
  const someVisibleSelected = visibleTasks.some((t) => selectedTasks.has(t.id))

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedTasks((prev) => {
        const next = new Set(prev)
        for (const t of visibleTasks) next.add(t.id)
        return next
      })
    } else {
      setSelectedTasks((prev) => {
        const next = new Set(prev)
        for (const t of visibleTasks) next.delete(t.id)
        return next
      })
    }
  }

  const hasError = tasksError || projectsError

  return (
    <div className="flex flex-col h-full text-slate-100 bg-slate-900">
      {/* Header */}
      <div className="flex items-center justify-between px-5 pl-12 lg:pl-5 py-3 border-b border-slate-700/60 shrink-0 bg-slate-800/40">
        <div className="flex items-center gap-2.5">
          <h1 className="text-base font-bold text-white tracking-tight">Dev Workflow</h1>
          {hasError && (
            <span className="text-[11px] text-red-300 bg-red-900/60 px-2 py-0.5 rounded-md border border-red-700">
              API error
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setDomainMapOpen(true)}
            className="text-sm text-slate-400 hover:text-white transition-colors"
            aria-label="Domain map settings"
            title="Domain Map"
          >
            ⚙
          </button>
          <a
            href="http://localhost:7070"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] text-blue-300 hover:text-blue-200 font-medium"
          >
            Dev Site ↗
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] text-blue-300 hover:text-blue-200 font-medium"
          >
            GitHub ↗
          </a>
        </div>
      </div>

      {/* Project summary cards */}
      <div className="flex flex-wrap gap-2 px-5 py-3 border-b border-slate-700/60 shrink-0">
        <ProjectCard
          label="All"
          open={allCounts.open}
          inProgress={allCounts.inProgress}
          done={allCounts.done}
          active={projectFilter === ''}
          onClick={() => setProjectFilter('')}
        />
        {(projects ?? []).map((p) => (
          <ProjectCard
            key={p.project_id}
            label={p.project_name}
            open={p.open_count}
            inProgress={p.in_progress_count}
            done={p.done_count}
            active={projectFilter === p.project_id}
            onClick={() => handleProjectClick(p.project_id)}
          />
        ))}
        {projectsError && (
          <span className="text-[11px] text-red-300">Failed to load projects</span>
        )}
      </div>

      {/* Phase strip */}
      <div className="flex flex-wrap items-center gap-1.5 px-5 py-2.5 border-b border-slate-700/60 shrink-0">
        {PHASES.map((phase) => (
          <PhaseChip
            key={phase.key}
            phase={phase}
            count={phaseCounts[phase.key] ?? 0}
            active={phaseFilter === phase.key}
            onClick={() => handlePhaseClick(phase.key)}
          />
        ))}
        {phaseFilter && (
          <button
            onClick={() => setPhaseFilter('')}
            className="text-[11px] text-slate-400 hover:text-white ml-1 underline shrink-0"
          >
            clear
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 px-5 py-2.5 border-b border-slate-700/60 shrink-0 bg-slate-800/30">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by ID or title..."
          className="text-xs bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-slate-200 w-full sm:w-52 placeholder-slate-500 focus:border-blue-500 focus:outline-none transition-colors"
        />
        <select
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
          className="text-xs bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-slate-200 flex-1 sm:flex-none"
        >
          <option value="">All Projects</option>
          {(projects ?? []).map((p) => (
            <option key={p.project_id} value={p.project_id}>
              {p.project_name}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-xs bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-slate-200 flex-1 sm:flex-none"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className="text-[11px] text-slate-400 ml-auto font-medium">
          {visibleTasks.length} task{visibleTasks.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Misplaced tasks banner */}
      <MisplacedBanner projectFilter={projectFilter} />

      {/* Task list */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {tasks === undefined && !tasksError && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-slate-500">Loading...</span>
          </div>
        )}
        {tasksError && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-red-300">Failed to load tasks</span>
          </div>
        )}
        {tasks !== undefined && visibleTasks.length === 0 && !tasksError && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-slate-500">No tasks found</span>
          </div>
        )}

        {/* Select-all header row */}
        {visibleTasks.length > 0 && (
          <div className="flex items-center gap-2.5 px-3 py-1.5 mb-1">
            <input
              type="checkbox"
              checked={allVisibleSelected}
              ref={(el) => {
                if (el) el.indeterminate = someVisibleSelected && !allVisibleSelected
              }}
              onChange={(e) => handleSelectAll(e.target.checked)}
              className="shrink-0 accent-blue-400 cursor-pointer"
              aria-label="Select all visible tasks"
            />
            <span className="text-[11px] text-slate-400 font-medium">
              {selectedTasks.size > 0 ? `${selectedTasks.size} selected` : 'Select all'}
            </span>
          </div>
        )}

        <div className="flex flex-col gap-0.5">
          {visibleTasks.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              selected={selectedTasks.has(task.id)}
              onSelect={handleSelectTask}
              onOpenDetail={(id) =>
                setDrawerTaskId((prev) => (prev === id ? null : id))
              }
            />
          ))}
        </div>
      </div>

      {/* Task detail drawer */}
      <TaskDetailDrawer
        taskId={drawerTaskId}
        onClose={() => setDrawerTaskId(null)}
      />

      {/* Bulk actions toolbar */}
      <BulkActions
        selectedIds={selectedTasks}
        projects={projects ?? []}
        onClearSelection={() => setSelectedTasks(new Set())}
      />

      {/* Domain map modal */}
      {domainMapOpen && (
        <DomainMapModal
          projects={projects ?? []}
          onClose={() => setDomainMapOpen(false)}
        />
      )}
    </div>
  )
}
