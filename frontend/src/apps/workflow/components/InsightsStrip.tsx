import type { InsightsStep } from '../types'
import { getStepLabel } from '../lib/pipeline'
import { formatDuration } from '../lib/time'

interface InsightsStripProps {
  steps: InsightsStep[]
}

function getNodeColor(step: InsightsStep): string {
  if (step.fail_rate > 0.10) return 'bg-red-500'
  if (step.fail_rate > 0.05 || step.skip_rate > 0.30) return 'bg-amber-500'
  return 'bg-emerald-500'
}

function getTextColor(step: InsightsStep): string {
  if (step.fail_rate > 0.10) return 'text-red-400'
  if (step.fail_rate > 0.05 || step.skip_rate > 0.30) return 'text-amber-400'
  return 'text-emerald-400'
}

export default function InsightsStrip({ steps }: InsightsStripProps) {
  if (steps.length === 0) return null

  return (
    <div className="flex items-start gap-0.5 overflow-x-auto pb-1">
      {steps.map((step, i) => (
        <div key={step.name} className="flex items-start">
          {i > 0 && (
            <div className="w-4 h-0.5 bg-gray-700 mt-[6px] shrink-0" />
          )}
          <button
            className="flex flex-col items-center gap-1 group cursor-pointer min-w-[52px]"
            title={`${step.name}: avg ${formatDuration(step.avg_duration_s)}, skip ${Math.round(step.skip_rate * 100)}%, fail ${Math.round(step.fail_rate * 100)}%`}
          >
            <div
              className={`w-3 h-3 rounded-full ${getNodeColor(step)}
                group-hover:ring-2 group-hover:ring-white/30 transition-all`}
            />
            <span className="text-[10px] text-gray-400">
              {getStepLabel(step.name)}
            </span>
            <span className={`text-[10px] ${getTextColor(step)}`}>
              ~{formatDuration(step.avg_duration_s)}
            </span>
            {step.skip_rate > 0 && (
              <span className="text-[10px] text-amber-500">
                {Math.round(step.skip_rate * 100)}% skip
              </span>
            )}
            {step.fail_rate > 0 && (
              <span className="text-[10px] text-red-400">
                {Math.round(step.fail_rate * 100)}% fail
              </span>
            )}
          </button>
        </div>
      ))}
    </div>
  )
}
