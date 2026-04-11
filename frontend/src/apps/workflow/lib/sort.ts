/**
 * Pure multi-criteria sort for Task rows.
 *
 * Design:
 *  - Pure function — no React, no DOM, easy to reason about and unit test.
 *  - Stable: original index used as the final tiebreaker so equal rows keep
 *    their incoming order across re-sorts.
 *  - Sorting NEVER hides rows — only reorders them.
 *  - Unknown enum values (priority/status) sort to the end deterministically.
 */

import { Priority, Status } from './tokens'
import type { SortDirection, SortFieldKey } from './tokens'
import type { Task } from '../types'

export interface SortCriterion {
  field: SortFieldKey
  dir: SortDirection
}

/** Default sort applied when the user has not configured anything. */
export const DEFAULT_SORT: readonly SortCriterion[] = [
  { field: 'status',     dir: 'asc'  },
  { field: 'priority',   dir: 'asc'  },
  { field: 'updated_at', dir: 'desc' },
]

/**
 * Extract the comparable value for a given field. Numeric where possible
 * (so we can subtract), string otherwise (compared with localeCompare).
 *
 * Strings are normalized to lowercase to keep "Apple" and "apple" adjacent.
 * Date strings (ISO) are converted to epoch ms — works because the API
 * returns ISO timestamps for created_at / updated_at.
 */
function extract(task: Task, field: SortFieldKey): number | string {
  switch (field) {
    case 'id':
      return task.id

    case 'created_at':
    case 'updated_at': {
      const raw = task[field]
      if (!raw) return Number.NEGATIVE_INFINITY
      const t = Date.parse(raw)
      return Number.isNaN(t) ? Number.NEGATIVE_INFINITY : t
    }

    case 'priority': {
      const order = Priority.order as Record<string, number>
      return Object.hasOwn(order, task.priority) ? order[task.priority]! : 99
    }

    case 'status': {
      const order = Status.order as Record<string, number>
      return Object.hasOwn(order, task.status) ? order[task.status]! : 99
    }

    case 'title':
      return task.title.toLowerCase()
  }
}

function compareValues(a: number | string, b: number | string): number {
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' })
}

/**
 * Apply an ordered list of sort criteria to a task array.
 * Returns a new array — does NOT mutate input.
 *
 * Empty criteria → returns the input as-is (preserved order).
 * Final tiebreaker → original index, to guarantee stability across renders.
 */
export function applySorts(tasks: readonly Task[], criteria: readonly SortCriterion[]): Task[] {
  if (tasks.length === 0) return []
  if (criteria.length === 0) return tasks.slice()

  const indexed = tasks.map((task, index) => ({ task, index }))

  indexed.sort((a, b) => {
    for (const c of criteria) {
      const av = extract(a.task, c.field)
      const bv = extract(b.task, c.field)
      const cmp = compareValues(av, bv)
      if (cmp !== 0) return c.dir === 'asc' ? cmp : -cmp
    }
    // Stable tiebreaker — original position wins.
    return a.index - b.index
  })

  return indexed.map((x) => x.task)
}

// ── URL serialization ─────────────────────────────────────────────────────
//
// Format: `field:dir,field:dir` (e.g. `status:asc,updated_at:desc`).
// Compact, human-readable, and back-button safe.

const VALID_FIELDS = new Set<SortFieldKey>(['id', 'created_at', 'updated_at', 'status', 'title', 'priority'])

export function serializeSort(criteria: readonly SortCriterion[]): string {
  return criteria.map((c) => `${c.field}:${c.dir}`).join(',')
}

export function parseSort(raw: string | null | undefined): SortCriterion[] {
  if (!raw) return []
  const out: SortCriterion[] = []
  const seen = new Set<SortFieldKey>()
  for (const part of raw.split(',')) {
    const [field, dir] = part.split(':') as [string, string | undefined]
    if (!VALID_FIELDS.has(field as SortFieldKey)) continue
    if (seen.has(field as SortFieldKey)) continue
    const direction: SortDirection = dir === 'desc' ? 'desc' : 'asc'
    out.push({ field: field as SortFieldKey, dir: direction })
    seen.add(field as SortFieldKey)
  }
  return out
}
