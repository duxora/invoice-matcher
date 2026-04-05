import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ingestAll } from '../lib/api'

export default function SourcesPage() {
  const [isIngesting, setIsIngesting] = useState(false)
  const [ingestOutput, setIngestOutput] = useState<string | null>(null)
  const [ingestError, setIngestError] = useState<string | null>(null)

  async function handleIngestAll() {
    setIsIngesting(true)
    setIngestOutput(null)
    setIngestError(null)
    try {
      const output = await ingestAll()
      setIngestOutput(output)
    } catch (err) {
      setIngestError(err instanceof Error ? err.message : 'Ingest failed')
    } finally {
      setIsIngesting(false)
    }
  }

  return (
    <div className="bg-gray-950 text-gray-100 p-4 overflow-y-auto min-h-full">
      <Link
        to="/kb"
        className="text-gray-500 hover:text-gray-300 text-sm mb-4 inline-block"
      >
        &larr; Back to Knowledge Base
      </Link>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Configured Sources</h1>
        <button
          onClick={handleIngestAll}
          disabled={isIngesting}
          className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded transition-colors"
        >
          {isIngesting ? 'Running…' : 'Run Full Scrape'}
        </button>
      </div>

      {/* Ingest status output */}
      {(ingestOutput || ingestError) && (
        <div
          className={`mb-4 rounded p-3 border text-sm ${
            ingestError
              ? 'bg-red-900/30 border-red-700 text-red-300'
              : 'bg-gray-800/50 border-gray-700'
          }`}
          role="status"
          aria-live="polite"
        >
          {ingestError ? (
            <p>{ingestError}</p>
          ) : (
            <pre className="text-xs text-gray-400 whitespace-pre-wrap">{ingestOutput}</pre>
          )}
        </div>
      )}

      {/* Sources note — the backend YAML is not exposed via JSON API */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-6 text-center">
        <p className="text-gray-400 text-sm mb-2">
          Source configuration is managed via <code className="bg-gray-900 px-1 py-0.5 rounded text-xs">sources.yaml</code> on the server.
        </p>
        <p className="text-gray-500 text-xs">
          To view or edit sources, open{' '}
          <code className="bg-gray-900 px-1 py-0.5 rounded">~/workspace/tools/local-kb/sources.yaml</code>{' '}
          in your editor, or visit the{' '}
          <a
            href="/kb/sources"
            className="text-blue-400 hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            Jinja sources page
          </a>{' '}
          for the table view.
        </p>
        <p className="text-gray-500 text-xs mt-3">
          Use <strong>Run Full Scrape</strong> above to ingest all configured sources.
        </p>
      </div>
    </div>
  )
}
