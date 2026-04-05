import { useState, useMemo, useCallback } from 'react'
import type { Task } from '../types'
import { useTaskBoard } from '../hooks/useTaskBoard'
import TaskDetailDrawer from './TaskDetailDrawer'
import BulkActions from './BulkActions'
import DomainMapModal from './DomainMapModal'
import MisplacedBanner from './MisplacedBanner'

// ── constants ──────────────────────────────────────────────────────────────

const PHASES = [
  { key: 'intake', label: 'Intake', color: 'text-blue-400 bg-blue-950 border-blue-800' },
  { key: 'backlog', label: 'Backlog', color: 'text-indigo-400 bg-indigo-950 border-indigo-800' },
  { key: 'implement', label: 'Implement', color: 'text-green-400 bg-green-950 border-green-800' },
  { key: 'pr_ci', label: 'PR / CI', color: 'text-amber-400 bg-amber-950 border-amber-800' },
  { key: 'review', label: 'Review', color: 'text-orange-400 bg-orange-950 border-orange-800' },
  { key: 'deploy', label: 'Deploy', color: 'text-purple-400 bg-purple-950 border-purple-800' },
  { key: 'verify', label: 'Verify', color: 'text-teal-400 bg-teal-950 border-teal-800' },
  { key: 'close', label: 'Close', color: 'text-gray-400 bg-gray-800 border-gray-700' },
] as const

type PhaseKey = (typeof PHASES)[number]['key']

const PRIORITY_BADGE: Record<string, string> = {
  critical: 'bg-red-950 text-red-400 border border-red-800',
  high: 'bg-orange-950 text-orange-400 border border-orange-800',
  medium: 'bg-yellow-950 text-yellow-400 border border-yellow-800',
  low: 'bg-gray-800 text-gray-500 border border-gray-700',
}

const STATUS_BADGE: Record<string, string> = {
  open: 'bg-blue-950 text-blue-400 border border-blue-800',
  in_progress: 'bg-amber-950 text-amber-400 border border-amber-800',
  backlog: 'bg-indigo-950 text-indigo-400 border border-indigo-800',
  done: 'bg-green-950 text-green-400 border border-green-800',
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
      className={`flex-shrink-0 flex flex-col gap-1 px-3 py-2 rounded-lg border transition-colors text-left ${
        active
          ? 'bg-gray-800 border-blue-500'
          : 'bg-gray-800 border-gray-700 hover:border-gray-600'
      }`}
    >
      <span className="text-xs font-medium text-gray-200 truncate max-w-[120px]">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-blue-400">{open} open</span>
        <span className="text-[10px] text-amber-400">{inProgress} in prog</span>
        <span className="text-[10px] text-green-400">{done} done</span>
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
      className={`flex items-center gap-1.5 px-2 py-1 rounded border text-[10px] font-medium transition-colors ${phase.color} ${
        active ? 'ring-1 ring-blue-400' : 'opacity-70 hover:opacity-100'
      }`}
    >
      <span>{phase.label}</span>
      {count > 0 && (
        <span className="bg-gray-950/60 px-1 rounded text-[9px]">{count}</span>
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
      className={`flex items-center gap-2 px-3 py-2 rounded border transition-colors ${
        selected
          ? 'bg-gray-800 border-gray-600'
          : 'border-transparent hover:bg-gray-800 hover:border-gray-700'
      }`}
    >
      {/* Checkbox */}
      <input
        type="checkbox"
        checked={selected}
        onChange={(e) => onSelect(task.id, e.target.checked)}
        onClick={(e) => e.stopPropagation()}
        className="shrink-0 accent-blue-500 cursor-pointer"
        aria-label={`Select task #${task.id}`}
      />

      {/* ID */}
      <span className="text-[10px] text-gray-600 w-10 shrink-0 text-right">#{task.id}</span>

      {/* Title — click to open detail */}
      <button
        className="text-xs text-gray-300 truncate flex-1 min-w-0 text-left hover:text-gray-100 transition-colors"
        onClick={() => onOpenDetail(task.id)}
      >
        {task.title}
      </button>

      {/* Priority */}
      <span
        className={`text-[10px] px-1.5 py-0.5 rounded ${PRIORITY_BADGE[task.priority] ?? 'bg-gray-800 text-gray-500'}`}
      >
        {task.priority}
      </span>

      {/* Status */}
      <span
        className={`text-[10px] px-1.5 py-0.5 rounded w-20 text-center ${STATUS_BADGE[task.status] ?? 'bg-gray-800 text-gray-400'}`}
      >
        {task.status.replace('_', ' ')}
      </span>

      {/* Project */}
      <span className="text-[10px] text-gray-500 w-24 truncate shrink-0">
        {task.project_name ?? task.project_id}
      </span>

      {/* Domain */}
      {task.domain ? (
        <span className="text-[10px] text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded shrink-0">
          {task.domain}
        </span>
      ) : (
        <span className="w-12 shrink-0" />
      )}

      {/* PR link */}
      {task.pr_number != null ? (
        <a
          href={`https://github.com/search?q=${encodeURIComponent(task.branch ?? String(task.pr_number))}`}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-[10px] text-blue-500 hover:text-blue-400 shrink-0"
        >
          PR#{task.pr_number}
        </a>
      ) : (
        <span className="w-10 shrink-0" />
      )}
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

  // Client-side filtering: search + phase
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
    return result
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
    <div className="flex flex-col h-full text-gray-100 bg-gray-950">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-semibold text-gray-100">Dev Workflow</h1>
          {hasError && (
            <span className="text-[10px] text-red-400 bg-red-950 px-1.5 py-0.5 rounded border border-red-800">
              API error
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Settings gear — opens domain map modal */}
          <button
            onClick={() => setDomainMapOpen(true)}
            className="text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
            aria-label="Domain map settings"
            title="Domain Map"
          >
            ⚙
          </button>
          <a
            href="http://localhost:7070"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-blue-400 hover:text-blue-300"
          >
            Dev Site
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-blue-400 hover:text-blue-300"
          >
            GitHub
          </a>
        </div>
      </div>

      {/* Project summary cards */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 overflow-x-auto shrink-0">
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
          <span className="text-[10px] text-red-400">Failed to load projects</span>
        )}
      </div>

      {/* Phase strip */}
      <div className="flex items-center gap-1.5 px-4 py-2 border-b border-gray-800 overflow-x-auto shrink-0">
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
            className="text-[10px] text-gray-500 hover:text-gray-300 ml-1 underline shrink-0"
          >
            clear
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 shrink-0">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by ID or title..."
          className="text-xs bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300 w-52 placeholder-gray-600"
        />
        <select
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
          className="text-xs bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300"
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
          className="text-xs bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className="text-[10px] text-gray-600 ml-auto">
          {visibleTasks.length} task{visibleTasks.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Misplaced tasks banner */}
      <MisplacedBanner projectFilter={projectFilter} />

      {/* Task list */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {tasks === undefined && !tasksError && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">Loading...</span>
          </div>
        )}
        {tasksError && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-red-400">Failed to load tasks</span>
          </div>
        )}
        {tasks !== undefined && visibleTasks.length === 0 && !tasksError && (
          <div className="flex items-center justify-center h-24">
            <span className="text-xs text-gray-600">No tasks found</span>
          </div>
        )}

        {/* Select-all header row */}
        {visibleTasks.length > 0 && (
          <div className="flex items-center gap-2 px-3 py-1 mb-0.5">
            <input
              type="checkbox"
              checked={allVisibleSelected}
              ref={(el) => {
                if (el) el.indeterminate = someVisibleSelected && !allVisibleSelected
              }}
              onChange={(e) => handleSelectAll(e.target.checked)}
              className="shrink-0 accent-blue-500 cursor-pointer"
              aria-label="Select all visible tasks"
            />
            <span className="text-[10px] text-gray-600">
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
