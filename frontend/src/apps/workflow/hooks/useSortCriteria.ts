/**
 * useSortCriteria — manages multi-criteria sort state with URL persistence.
 *
 * Behavior:
 *  - First mount: read from `?sort=` query param. If absent, fall back to
 *    localStorage. If neither, use the default.
 *  - On every change: write to URL (replaceState — no history bloat) AND
 *    localStorage so a fresh tab without query params still feels familiar.
 *  - Pure state container — components dispatch via the returned helpers.
 *
 * Why hand-rolled instead of a router? The workflow app already mounts inside
 * a Jinja-served HTML shell with a single SPA route. Adding a router for one
 * query param is overkill — `URLSearchParams` + `history.replaceState` is
 * 12 lines and zero deps.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  DEFAULT_SORT,
  parseSort,
  serializeSort,
  type SortCriterion,
} from '../lib/sort'
import { SortFieldMap, type SortDirection, type SortFieldKey } from '../lib/tokens'

const STORAGE_KEY = 'workflow.sortCriteria'
const URL_PARAM = 'sort'

function readInitial(): SortCriterion[] {
  if (typeof window === 'undefined') return DEFAULT_SORT.slice()

  const fromUrl = parseSort(new URLSearchParams(window.location.search).get(URL_PARAM))
  if (fromUrl.length > 0) return fromUrl

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    const parsed = parseSort(stored)
    if (parsed.length > 0) return parsed
  } catch {
    // localStorage may throw in private browsing — ignore and fall through.
  }

  return DEFAULT_SORT.slice()
}

function writeBack(criteria: readonly SortCriterion[]): void {
  if (typeof window === 'undefined') return

  const serialized = serializeSort(criteria)
  const url = new URL(window.location.href)
  if (serialized) {
    url.searchParams.set(URL_PARAM, serialized)
  } else {
    url.searchParams.delete(URL_PARAM)
  }
  window.history.replaceState(null, '', url.toString())

  try {
    window.localStorage.setItem(STORAGE_KEY, serialized)
  } catch {
    // ignore
  }
}

export interface UseSortCriteriaReturn {
  criteria: SortCriterion[]
  /** Append a field, or move it to the end if already present. */
  add: (field: SortFieldKey, dir?: SortDirection) => void
  /** Remove a field by key. No-op if absent. */
  remove: (field: SortFieldKey) => void
  /** Flip the direction of a single criterion. */
  toggleDir: (field: SortFieldKey) => void
  /** Reorder via dragging — moves `field` to the position of `targetField`. */
  reorder: (field: SortFieldKey, targetField: SortFieldKey) => void
  /**
   * Header-click cycle: none → asc → desc → removed.
   * If `append` is true, mutates in-place; otherwise replaces the whole list.
   */
  cycleHeader: (field: SortFieldKey, append: boolean) => void
  /** Reset to default sort. */
  reset: () => void
}

export function useSortCriteria(): UseSortCriteriaReturn {
  const [criteria, setCriteria] = useState<SortCriterion[]>(readInitial)

  // Persist to URL + localStorage on every change.
  useEffect(() => { writeBack(criteria) }, [criteria])

  const add = useCallback((field: SortFieldKey, dir?: SortDirection) => {
    setCriteria((prev) => {
      const next = prev.filter((c) => c.field !== field)
      next.push({ field, dir: dir ?? SortFieldMap[field].defaultDir })
      return next
    })
  }, [])

  const remove = useCallback((field: SortFieldKey) => {
    setCriteria((prev) => prev.filter((c) => c.field !== field))
  }, [])

  const toggleDir = useCallback((field: SortFieldKey) => {
    setCriteria((prev) =>
      prev.map((c) => (c.field === field ? { ...c, dir: c.dir === 'asc' ? 'desc' : 'asc' } : c)),
    )
  }, [])

  const reorder = useCallback((field: SortFieldKey, targetField: SortFieldKey) => {
    if (field === targetField) return
    setCriteria((prev) => {
      const fromIdx = prev.findIndex((c) => c.field === field)
      const toIdx   = prev.findIndex((c) => c.field === targetField)
      if (fromIdx === -1 || toIdx === -1) return prev
      const next = prev.slice()
      const [moved] = next.splice(fromIdx, 1)
      if (!moved) return prev
      next.splice(toIdx, 0, moved)
      return next
    })
  }, [])

  const cycleHeader = useCallback((field: SortFieldKey, append: boolean) => {
    setCriteria((prev) => {
      const existing = prev.find((c) => c.field === field)
      const base = append ? prev.filter((c) => c.field !== field) : []

      if (!existing) {
        return [...base, { field, dir: SortFieldMap[field].defaultDir }]
      }
      if (existing.dir === 'asc') {
        return [...base, { field, dir: 'desc' }]
      }
      // Was desc → cycle removes it.
      return base
    })
  }, [])

  const reset = useCallback(() => setCriteria(DEFAULT_SORT.slice()), [])

  return { criteria, add, remove, toggleDir, reorder, cycleHeader, reset }
}
