import type { PipelineState, DetailTarget } from '../types'
import PipelineStrip from './PipelineStrip'

interface PipelineListProps {
  pipelines: PipelineState[]
  onSelect: (target: DetailTarget) => void
}

export default function PipelineList({ pipelines, onSelect }: PipelineListProps) {
  if (pipelines.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500 py-12">
        <p className="text-sm">No active pipelines</p>
        <p className="text-xs mt-1">
          Claim a task with <code className="bg-gray-800 px-1 rounded">tkt_next</code> or launch from backlog below
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      {pipelines.map((p) => (
        <PipelineStrip key={p.session_id} pipeline={p} onSelect={onSelect} />
      ))}
    </div>
  )
}
