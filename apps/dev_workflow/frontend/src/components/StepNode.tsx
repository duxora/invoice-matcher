import type { StepStatus } from '../types'
import { getStepColor, getStepLabel } from '../lib/pipeline'

interface StepNodeProps {
  stepName: string
  status: StepStatus
  isActive: boolean
  isStale: boolean
  onClick: () => void
}

export default function StepNode({ stepName, status, isActive, isStale, onClick }: StepNodeProps) {
  const displayStatus = isStale && isActive ? 'stale' : isActive ? 'active' : status
  const color = getStepColor(displayStatus)
  const label = getStepLabel(stepName)
  const isSkipped = status === 'skipped'
  const pulse = (isActive && !isStale) ? 'animate-pulse' : ''
  const stalePulse = (isActive && isStale) ? 'animate-pulse' : ''

  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className="flex flex-col items-center gap-1 group cursor-pointer"
      title={`${stepName}: ${displayStatus}`}
    >
      <div
        className={`w-3 h-3 rounded-full ${color} ${pulse} ${stalePulse}
          group-hover:ring-2 group-hover:ring-white/30 transition-all`}
      />
      <span className={`text-[10px] ${isSkipped ? 'line-through text-gray-600' : 'text-gray-400'}`}>
        {label}
      </span>
    </button>
  )
}
