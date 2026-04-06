import type { InsightsAlert } from '../types'
import { getStepLabel } from '../lib/pipeline'

interface InsightAlertsProps {
  alerts: InsightsAlert[]
}

function alertConfig(type: InsightsAlert['type']): {
  prefix: string
  bg: string
  border: string
  text: string
} {
  switch (type) {
    case 'bottleneck':
      return { prefix: '⏱ Bottleneck', bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400' }
    case 'high_fail':
      return { prefix: '✗ High failure', bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400' }
    case 'high_skip':
      return { prefix: '⊘ Often skipped', bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400' }
  }
}

export default function InsightAlerts({ alerts }: InsightAlertsProps) {
  if (alerts.length === 0) return null

  return (
    <div className="flex flex-col gap-2">
      {alerts.map((alert, i) => {
        const config = alertConfig(alert.type)
        return (
          <div
            key={i}
            className={`${config.bg} border ${config.border} rounded-lg px-4 py-3 flex items-start gap-2`}
          >
            <span className={`text-xs font-semibold ${config.text} shrink-0`}>
              {config.prefix}
            </span>
            <span className="text-xs text-gray-300">
              <span className="font-medium">{getStepLabel(alert.step)}</span>
              {' — '}
              {alert.message}
            </span>
          </div>
        )
      })}
    </div>
  )
}
