import { useMemo, useCallback } from 'react'
import type { DetailTarget, PipelineType } from '../types'
import { usePipelineState } from '../hooks/usePipelineState'
import { useNotifications } from '../hooks/useNotifications'
import { useUrlParam } from '../hooks/useUrlParam'
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

  const [projectFilter, setProjectFilter] = useUrlParam('project')
  const [typeFilterRaw, setTypeFilter]    = useUrlParam('type')
  const typeFilter = typeFilterRaw as PipelineType | ''
  const [detailKey, setDetailKey]         = useUrlParam('detail')

  // Rehydrate the detail target from the URL once the pipelines list arrives.
  // URL format: "pipeline:<task_id>" or "step:<task_id>:<stepName>".
  // Session/task kinds aren't produced from PipelinesPage's flow, so we don't
  // encode them here.
  const selected = useMemo<DetailTarget | null>(() => {
    if (!detailKey) return null
    const [kind, idStr, ...rest] = detailKey.split(':')
    const taskId = Number(idStr)
    if (!Number.isFinite(taskId)) return null
    const pipeline = pipelines.find((p) => p.task_id === taskId)
    if (!pipeline) return null
    if (kind === 'pipeline') return { kind: 'pipeline', pipeline }
    if (kind === 'step' && rest.length > 0) {
      return { kind: 'step', pipeline, stepName: rest.join(':') }
    }
    return null
  }, [detailKey, pipelines])

  const setSelected = useCallback(
    (target: DetailTarget | null) => {
      if (!target) { setDetailKey(''); return }
      if (target.kind === 'pipeline') {
        setDetailKey(`pipeline:${target.pipeline.task_id}`)
      } else if (target.kind === 'step') {
        setDetailKey(`step:${target.pipeline.task_id}:${target.stepName}`)
      } else {
        // session/task detail panels aren't triggered from this page
        setDetailKey('')
      }
    },
    [setDetailKey],
  )

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
