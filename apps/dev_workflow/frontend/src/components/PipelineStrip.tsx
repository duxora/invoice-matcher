import type { PipelineState, DetailTarget } from '../types'
import { getStepOrder, getActiveStep, getLineColor, getPipelineProgress } from '../lib/pipeline'
import { formatElapsed } from '../lib/time'
import StepNode from './StepNode'

interface PipelineStripProps {
  pipeline: PipelineState
  onSelect: (target: DetailTarget) => void
}

export default function PipelineStrip({ pipeline, onSelect }: PipelineStripProps) {
  const steps = getStepOrder(pipeline.pipeline, pipeline.size)
  const activeStep = getActiveStep(pipeline)
  const { done, total } = getPipelineProgress(pipeline)
  const pipelineLabel = pipeline.pipeline === 'code'
    ? `code/${pipeline.size}`
    : pipeline.pipeline

  return (
    <div
      className="bg-gray-900 border border-gray-800 rounded-lg p-3 hover:border-gray-700 transition-colors cursor-pointer"
      onClick={() => onSelect({ kind: 'pipeline', pipeline })}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-200">
            #{pipeline.task_id}
          </span>
          <span className="text-sm text-gray-400 truncate max-w-xs">
            {pipeline.title}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 shrink-0">
          <span className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-400">
            {pipelineLabel}
          </span>
          {pipeline.domain && (
            <span className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-400">
              {pipeline.domain}
            </span>
          )}
          <span>{done}/{total}</span>
          <span>⏱ {formatElapsed(pipeline.started_at)}</span>
          {pipeline.stale && (
            <span className="px-1.5 py-0.5 bg-amber-900/50 text-amber-400 rounded">
              stale
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-0.5">
        {steps.map((step, i) => {
          const state = pipeline.steps[step]
          if (!state) return null
          const isActive = step === activeStep
          const lineStatus = state.status === 'done' ? 'done'
            : state.status === 'failed' ? 'failed'
            : 'pending' as const
          return (
            <div key={step} className="flex items-center">
              {i > 0 && (
                <div className={`w-4 h-0.5 ${getLineColor(lineStatus)}`} />
              )}
              <StepNode
                stepName={step}
                status={state.status}
                isActive={isActive}
                isStale={pipeline.stale}
                onClick={() => onSelect({ kind: 'step', pipeline, stepName: step })}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
