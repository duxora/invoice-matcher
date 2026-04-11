/**
 * SortPill — single sort criterion as an interactive pill.
 *
 * Anatomy (left → right):
 *   ┌──────────────────────────────────────────────┐
 *   │ ⠿ [position]  Field ↑  ✕                     │
 *   └──────────────────────────────────────────────┘
 *
 *  - drag handle  → reorder pills (changes precedence)
 *  - position #   → numeric badge showing sort precedence (1, 2, 3…)
 *  - field label  → clickable to flip direction
 *  - direction    → ↑ asc / ↓ desc, also clickable
 *  - ✕ button     → remove this criterion
 *
 * The pill is a single token-aware atom. No state, no API calls — pure
 * presentation + event delegation. All visual semantics live in tokens.ts.
 */

import { ArrowDownIcon, ArrowUpIcon, CloseIcon, GripVerticalIcon } from './icons'
import type { SortDirection, SortFieldKey } from '../../lib/tokens'
import { SortFieldMap } from '../../lib/tokens'

interface SortPillProps {
  field: SortFieldKey
  dir: SortDirection
  position: number
  total: number
  isDragging?: boolean
  isDropTarget?: boolean
  onToggleDir: (field: SortFieldKey) => void
  onRemove: (field: SortFieldKey) => void
  onDragStart: (field: SortFieldKey) => void
  onDragOver: (field: SortFieldKey) => void
  onDragEnd: () => void
}

export function SortPill({
  field,
  dir,
  position,
  total,
  isDragging,
  isDropTarget,
  onToggleDir,
  onRemove,
  onDragStart,
  onDragOver,
  onDragEnd,
}: SortPillProps) {
  const def = SortFieldMap[field]
  const isPrimary = position === 1
  const dirLabel = dir === 'asc' ? 'ascending' : 'descending'
  const dirArrow = dir === 'asc'
    ? <ArrowUpIcon size={9} className="text-slate-300" />
    : <ArrowDownIcon size={9} className="text-slate-300" />

  // Primary pill gets a slightly stronger border tone — quick visual scan
  // signal that this field dominates the sort. All colors live in this file
  // because they apply ONLY to the SortPill atom (not domain semantics).
  const baseClasses = isPrimary
    ? 'border-blue-700/60 bg-blue-950/40 text-blue-100'
    : 'border-slate-700/60 bg-slate-800/80 text-slate-200'

  const dropClasses = isDropTarget
    ? 'ring-1 ring-blue-400/70 ring-offset-1 ring-offset-slate-900'
    : ''

  const draggingClasses = isDragging ? 'opacity-40 scale-95' : 'opacity-100'

  return (
    <div
      role="group"
      aria-label={`Sort by ${def.label}, ${dirLabel}, position ${position} of ${total}`}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = 'move'
        // Required for Firefox to actually start drag.
        e.dataTransfer.setData('text/plain', field)
        onDragStart(field)
      }}
      onDragOver={(e) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = 'move'
        onDragOver(field)
      }}
      onDrop={(e) => e.preventDefault()}
      onDragEnd={onDragEnd}
      className={`
        inline-flex items-center gap-1 pl-1 pr-1.5 py-1 rounded-full border
        text-[11px] font-medium select-none transition-all
        ${baseClasses} ${dropClasses} ${draggingClasses}
      `}
    >
      {/* Drag handle */}
      <span
        className="cursor-grab text-slate-500 hover:text-slate-200 active:cursor-grabbing px-0.5"
        aria-hidden="true"
        title="Drag to reorder"
      >
        <GripVerticalIcon size={11} />
      </span>

      {/* Precedence badge */}
      <span
        className={`
          inline-flex items-center justify-center min-w-[14px] h-[14px] px-1
          rounded-full text-[9px] font-bold tabular-nums
          ${isPrimary ? 'bg-blue-500/80 text-white' : 'bg-slate-700 text-slate-300'}
        `}
        aria-hidden="true"
      >
        {position}
      </span>

      {/* Field label + direction (entire region toggles direction) */}
      <button
        type="button"
        onClick={() => onToggleDir(field)}
        className="inline-flex items-center gap-1 px-1 py-0.5 rounded hover:bg-white/10 transition-colors"
        aria-label={`${def.label} ${dirLabel}. Click to flip direction.`}
      >
        <span>{def.label}</span>
        {dirArrow}
      </button>

      {/* Remove */}
      <button
        type="button"
        onClick={() => onRemove(field)}
        className="ml-0.5 w-4 h-4 inline-flex items-center justify-center rounded-full text-slate-500 hover:text-white hover:bg-red-500/40 transition-colors"
        aria-label={`Remove ${def.label} sort`}
      >
        <CloseIcon size={8} />
      </button>
    </div>
  )
}
