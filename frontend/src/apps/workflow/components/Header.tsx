interface HeaderProps {
  project: string
  onProjectChange: (project: string) => void
  pipelineFilter: string
  onPipelineFilterChange: (filter: string) => void
  activeSessionCount: number
}

export default function Header({
  project,
  onProjectChange,
  pipelineFilter,
  onPipelineFilterChange,
  activeSessionCount,
}: HeaderProps) {
  return (
    <header className="h-12 border-b border-gray-800 flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-gray-200">Dev Workflow</span>
        <input
          type="text"
          value={project}
          onChange={(e) => onProjectChange(e.target.value)}
          placeholder="Project filter..."
          className="text-xs bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300 w-40"
        />
        <select
          value={pipelineFilter}
          onChange={(e) => onPipelineFilterChange(e.target.value)}
          className="text-xs bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300"
        >
          <option value="all">All Pipelines</option>
          <option value="code">Code</option>
          <option value="research">Research</option>
          <option value="docs">Docs</option>
          <option value="solo-commit">Solo Commit</option>
        </select>
      </div>
      <div className="flex items-center gap-2">
        {activeSessionCount > 0 && (
          <span className="text-xs px-2 py-0.5 bg-emerald-900/50 text-emerald-400 rounded-full">
            {activeSessionCount} active
          </span>
        )}
      </div>
    </header>
  )
}
