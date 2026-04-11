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
    <footer className="h-8 border-t border-gray-800 flex items-center gap-4 px-4 text-[11px] text-gray-300">
      <span className={sseConnected ? 'text-emerald-400' : 'text-red-400'}>
        {sseLabel}
      </span>
      <span>
        {pipelineError ? (
          <span className="text-red-400">Pipeline API error</span>
        ) : (
          `${pipelineCount} active pipeline${pipelineCount !== 1 ? 's' : ''}`
        )}
      </span>
    </footer>
  )
}
