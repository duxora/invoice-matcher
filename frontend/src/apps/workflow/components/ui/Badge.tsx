/**
 * Atomic badge components for Priority and Status.
 * Single source of truth for badge appearance — delegates to design tokens.
 */

import { Priority, Status } from '../../lib/tokens'

interface PriorityBadgeProps {
  priority: string
  className?: string
}

export function PriorityBadge({ priority, className = '' }: PriorityBadgeProps) {
  const cls = Priority.badge[priority as keyof typeof Priority.badge] ?? Priority.fallback.badge
  const label = Priority.display[priority as keyof typeof Priority.display] ?? priority
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded ${cls} ${className}`}>
      {label}
    </span>
  )
}

interface StatusBadgeProps {
  status: string
  /** pill variant adds rounded-full (default: rounded) */
  pill?: boolean
  className?: string
}

export function StatusBadge({ status, pill = false, className = '' }: StatusBadgeProps) {
  const cls = Status.badge[status as keyof typeof Status.badge] ?? Status.fallback.badge
  const label = Status.display[status as keyof typeof Status.display] ?? status
  return (
    <span className={`text-[10px] px-1.5 py-px font-medium ${pill ? 'rounded-full' : 'rounded'} ${cls} ${className}`}>
      {label}
    </span>
  )
}

interface PriorityDotProps {
  priority: string
  title?: string
}

export function PriorityDot({ priority, title }: PriorityDotProps) {
  const cls = Priority.dot[priority as keyof typeof Priority.dot] ?? Priority.fallback.dot
  return (
    <span
      className={`shrink-0 w-1.5 h-1.5 rounded-full ${cls}`}
      title={title ?? priority}
    />
  )
}
