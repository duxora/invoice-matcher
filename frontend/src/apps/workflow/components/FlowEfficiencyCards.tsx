import type { InsightsFlowEfficiency } from '../types'
import { formatDuration } from '../lib/time'

interface FlowEfficiencyCardsProps {
  items: InsightsFlowEfficiency[]
}

export default function FlowEfficiencyCards({ items }: FlowEfficiencyCardsProps) {
  if (items.length === 0) return null

  return (
    <div className="flex flex-wrap gap-3">
      {items.map((item) => (
        <div
          key={item.size}
          className="bg-gray-900 border border-gray-800 rounded-lg p-4 min-w-[140px]"
        >
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            {item.size}
          </div>
          <div className="text-lg font-semibold text-gray-100 mb-1">
            {formatDuration(item.avg_duration_s)}
          </div>
          <div className="text-xs text-gray-500">
            {formatDuration(item.min_duration_s)} – {formatDuration(item.max_duration_s)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {item.count} run{item.count !== 1 ? 's' : ''}
          </div>
        </div>
      ))}
    </div>
  )
}
