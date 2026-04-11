/**
 * Workflow design tokens — single source of truth for all visual semantics.
 *
 * Rules:
 *  - Add a token here first, then use it in components.
 *  - Never hard-code a Tailwind class that encodes priority/status/phase meaning
 *    directly in a component. Always import from here.
 *  - `fallback` values cover unknown/future values gracefully.
 */

// ── Priority ───────────────────────────────────────────────────────────────

export const Priority = {
  /** Canonical sort order — lower = higher urgency */
  order: {
    critical: 0,
    high:     1,
    medium:   2,
    low:      3,
  },

  /** Left-border stripe on task rows — primary scan signal */
  stripe: {
    critical: 'border-l-red-500',
    high:     'border-l-orange-500',
    medium:   'border-l-yellow-500/70',
    low:      'border-l-slate-600/40',
  },

  /** Filled dot beside task title */
  dot: {
    critical: 'bg-red-500',
    high:     'bg-orange-500',
    medium:   'bg-yellow-500',
    low:      'bg-slate-600',
  },

  /** Muted text label (e.g., "critical" floating at row end) */
  label: {
    critical: 'text-red-400',
    high:     'text-orange-400',
    medium:   'text-yellow-400',
    low:      'text-slate-400',
  },

  /** Pill/badge used in detail views and meta rows */
  badge: {
    critical: 'bg-red-900/60 text-red-300 border border-red-700/50',
    high:     'bg-orange-900/60 text-orange-300 border border-orange-700/50',
    medium:   'bg-yellow-900/60 text-yellow-300 border border-yellow-700/50',
    low:      'bg-slate-800/60 text-slate-400 border border-slate-700/50',
  },

  /** Human-readable display strings */
  display: {
    critical: 'Critical',
    high:     'High',
    medium:   'Medium',
    low:      'Low',
  },

  /** Fallbacks for unknown/future priority values */
  fallback: {
    stripe:  'border-l-slate-600/40',
    dot:     'bg-slate-600',
    label:   'text-slate-400',
    badge:   'bg-slate-800/60 text-slate-400 border border-slate-700/50',
    display: 'Unknown',
  },
} as const

// ── Status ─────────────────────────────────────────────────────────────────

export const Status = {
  /**
   * Canonical sort order — lower = surfaces first.
   * Reflects "what needs my attention now" rather than alphabetical order:
   * actively-worked first, then ready-to-pick, then waiting, then resolved.
   */
  order: {
    in_progress: 0,
    open:        1,
    backlog:     2,
    done:        3,
  },

  /** Pill/badge for inline and detail view use */
  badge: {
    open:        'bg-blue-900/60 text-blue-300 border border-blue-700/50',
    in_progress: 'bg-amber-900/60 text-amber-300 border border-amber-700/50',
    backlog:     'bg-indigo-900/60 text-indigo-300 border border-indigo-700/50',
    done:        'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50',
  },

  /** Human-readable display strings */
  display: {
    open:        'Open',
    in_progress: 'In Progress',
    backlog:     'Backlog',
    done:        'Done',
  },

  /** Filter dropdown options */
  options: [
    { value: '',            label: 'Active' },
    { value: 'backlog',     label: 'Backlog only' },
    { value: 'open',        label: 'Open only' },
    { value: 'in_progress', label: 'In Progress only' },
    { value: 'done',        label: 'Done only' },
    { value: 'all',         label: 'All statuses' },
  ],

  /** Fallback for unknown/future status values */
  fallback: {
    badge:   'bg-slate-800/60 text-slate-400 border border-slate-700/50',
    display: 'Unknown',
  },
} as const

// ── Phase ──────────────────────────────────────────────────────────────────

export const Phases = [
  { key: 'intake',    label: 'Intake',    color: 'text-blue-300 bg-blue-900/40 border-blue-700/60',     dot: 'bg-blue-400'    },
  { key: 'backlog',   label: 'Backlog',   color: 'text-indigo-300 bg-indigo-900/40 border-indigo-700/60', dot: 'bg-indigo-400' },
  { key: 'implement', label: 'Implement', color: 'text-emerald-300 bg-emerald-900/40 border-emerald-700/60', dot: 'bg-emerald-400' },
  { key: 'pr_ci',     label: 'PR / CI',   color: 'text-amber-300 bg-amber-900/40 border-amber-700/60',   dot: 'bg-amber-400'   },
  { key: 'review',    label: 'Review',    color: 'text-orange-300 bg-orange-900/40 border-orange-700/60', dot: 'bg-orange-400' },
  { key: 'deploy',    label: 'Deploy',    color: 'text-purple-300 bg-purple-900/40 border-purple-700/60', dot: 'bg-purple-400' },
  { key: 'verify',    label: 'Verify',    color: 'text-teal-300 bg-teal-900/40 border-teal-700/60',      dot: 'bg-teal-400'    },
  { key: 'close',     label: 'Close',     color: 'text-gray-400 bg-gray-800/40 border-gray-600/60',      dot: 'bg-gray-500'    },
] as const

export type PhaseKey = (typeof Phases)[number]['key']

// ── Sort fields ────────────────────────────────────────────────────────────
//
// Single source of truth for sortable columns. Adding a new sortable field
// means: (1) extend the SortFieldKey union, (2) add it here, (3) handle the
// extraction in lib/sort.ts. Components read display strings from this map.

export type SortFieldKey = 'id' | 'created_at' | 'updated_at' | 'status' | 'title' | 'priority'
export type SortDirection = 'asc' | 'desc'

export interface SortFieldDef {
  key: SortFieldKey
  /** Short label used inside pills */
  label: string
  /** Longer label used in the "+ Add sort" menu */
  menuLabel: string
  /** Default direction when this field is added without an explicit one */
  defaultDir: SortDirection
}

export const SortFields: readonly SortFieldDef[] = [
  { key: 'status',     label: 'Status',   menuLabel: 'Status (workflow order)', defaultDir: 'asc'  },
  { key: 'priority',   label: 'Priority', menuLabel: 'Priority',                defaultDir: 'asc'  },
  { key: 'updated_at', label: 'Updated',  menuLabel: 'Last updated',            defaultDir: 'desc' },
  { key: 'created_at', label: 'Created',  menuLabel: 'Created date',            defaultDir: 'desc' },
  { key: 'id',         label: 'ID',       menuLabel: 'Ticket ID',               defaultDir: 'desc' },
  { key: 'title',      label: 'Name',     menuLabel: 'Name (A → Z)',            defaultDir: 'asc'  },
] as const

export const SortFieldMap: Record<SortFieldKey, SortFieldDef> = SortFields.reduce(
  (acc, f) => { acc[f.key] = f; return acc },
  {} as Record<SortFieldKey, SortFieldDef>,
)
