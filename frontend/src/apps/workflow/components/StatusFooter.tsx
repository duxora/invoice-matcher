interface StatusFooterProps {
  sseConnected: boolean
  lastSseEvent: Date | null
  pipelineCount: number
  pipelineError: Error | undefined
}

export default function StatusFooter({
  sseConnected,
  lastSseEvent,
  pipelineCount,
  pipelineError,
}: StatusFooterProps) {
  const sseLabel = sseConnected
    ? `SSE ● ${lastSseEvent ? lastSseEvent.toLocaleTimeString() : 'connected'}`
    : 'SSE ○ disconnected'

  return (
    <footer className="h-8 border-t border-gray-800 flex items-center gap-4 px-4 text-[10px] text-gray-500">
      <span className={sseConnected ? 'text-emerald-600' : 'text-red-600'}>
        {sseLabel}
      </span>
      <span>
        {pipelineError ? (
          <span className="text-red-600">Pipeline API error</span>
        ) : (
          `${pipelineCount} active pipeline${pipelineCount !== 1 ? 's' : ''}`
        )}
      </span>
    </footer>
  )
}
