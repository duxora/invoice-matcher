import { useState, useMemo } from 'react'
import type { DetailTarget, PipelineType } from '../types'
import { usePipelineState } from '../hooks/usePipelineState'
import { useNotifications } from '../hooks/useNotifications'
import PipelineList from '../components/PipelineList'
import DetailPanel from '../components/DetailPanel'

const PIPELINE_TYPES: { value: PipelineType | ''; label: string }[] = [
  { value: '', label: 'All types' },
  { value: 'code', label: 'Code' },
  { value: 'research', label: 'Research' },
  { value: 'docs', label: 'Docs' },
  { value: 'solo-commit', label: 'Solo commit' },
]

export default function PipelinesPage() {
  const { pipelines, error, isLoading } = usePipelineState()
  useNotifications(pipelines)

  const [projectFilter, setProjectFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState<PipelineType | ''>('')
  const [selected, setSelected] = useState<DetailTarget | null>(null)

  // Derive unique project names from pipelines
  const projects = useMemo(() => {
    const seen = new Set<string>()
    for (const p of pipelines) {
      if (p.domain) seen.add(p.domain)
    }
    return Array.from(seen).sort()
  }, [pipelines])

  const filtered = useMemo(() => {
    let result = pipelines
    if (projectFilter) {
      result = result.filter((p) => p.domain === projectFilter)
    }
    if (typeFilter) {
      result = result.filter((p) => p.pipeline === typeFilter)
    }
    return result
  }, [pipelines, projectFilter, typeFilter])

  return (
    <div className="flex flex-col h-full text-gray-100 bg-gray-950">
      {/* Filter bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 shrink-0">
        <select
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
          className="text-xs bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300"
          aria-label="Filter by domain"
        >
          <option value="">All domains</option>
          {projects.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as PipelineType | '')}
          className="text-xs bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300"
          aria-label="Filter by pipeline type"
        >
          {PIPELINE_TYPES.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <span className="text-[10px] text-gray-600 ml-auto">
          {isLoading && 'Loading...'}
          {!isLoading && `${filtered.length} pipeline${filtered.length !== 1 ? 's' : ''}`}
        </span>
        {error && (
          <span className="text-[10px] text-red-400 bg-red-950 px-1.5 py-0.5 rounded border border-red-800">
            API error
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {isLoading && (
            <div className="flex items-center justify-center h-24">
              <span className="text-xs text-gray-600">Loading pipelines...</span>
            </div>
          )}
          {!isLoading && (
            <PipelineList pipelines={filtered} onSelect={setSelected} />
          )}
        </div>

        {/* Detail panel */}
        {selected && (
          <div className="w-80 shrink-0 border-l border-gray-800">
            <DetailPanel target={selected} onClose={() => setSelected(null)} />
          </div>
        )}
      </div>
    </div>
  )
}
