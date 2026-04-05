import { useState, useCallback } from 'react'
import type { DetailTarget } from './types'
import { usePipelineState } from './hooks/usePipelineState'
import { useSessions } from './hooks/useSessions'
import { useTaskUpdates } from './hooks/useTaskUpdates'
import { useNotifications } from './hooks/useNotifications'
import Header from './components/Header'
import PipelineList from './components/PipelineList'
import SessionSidebar from './components/SessionSidebar'
import BacklogTable from './components/BacklogTable'
import DetailPanel from './components/DetailPanel'
import StatusFooter from './components/StatusFooter'

export default function App() {
  const [project, setProject] = useState('')
  const [pipelineFilter, setPipelineFilter] = useState('all')
  const [detailTarget, setDetailTarget] = useState<DetailTarget | null>(null)

  const { pipelines, error: pipelineError } = usePipelineState()
  const { sessions } = useSessions()
  const { tasks: backlogTasks, connected: sseConnected, lastEvent: lastSseEvent } = useTaskUpdates({
    status: 'open,backlog',
    project: project || undefined,
  })

  useNotifications(pipelines)

  const filteredPipelines = pipelines.filter((p) => {
    if (project && !p.title.toLowerCase().includes(project.toLowerCase())) return false
    if (pipelineFilter !== 'all' && p.pipeline !== pipelineFilter) return false
    return true
  })

  const activeSessions = sessions.filter((s) => s.alive)

  const handleSelect = useCallback((target: DetailTarget) => {
    setDetailTarget(target)
  }, [])

  const handleClose = useCallback(() => {
    setDetailTarget(null)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <Header
        project={project}
        onProjectChange={setProject}
        pipelineFilter={pipelineFilter}
        onPipelineFilterChange={setPipelineFilter}
        activeSessionCount={activeSessions.length}
      />

      <main className="flex-1 flex min-h-0">
        <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-4">
          <PipelineList pipelines={filteredPipelines} onSelect={handleSelect} />
          <BacklogTable tasks={backlogTasks} onSelect={handleSelect} />
        </div>

        <div className="w-56 border-l border-gray-800 p-3 overflow-y-auto">
          <SessionSidebar sessions={sessions} onSelect={handleSelect} />
        </div>

        {detailTarget && (
          <DetailPanel target={detailTarget} onClose={handleClose} />
        )}
      </main>

      <StatusFooter
        sseConnected={sseConnected}
        lastSseEvent={lastSseEvent}
        pipelineCount={filteredPipelines.length}
        pipelineError={pipelineError}
      />
    </div>
  )
}
