import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import useSWR from 'swr'
import { deleteEntry } from '../lib/api'
import { domainBadgeClass, confidenceBadgeClass, formatDate } from '../lib/domain'
import type { KBEntry } from '../types'

const fetcher = (url: string) => fetch(url).then((r) => r.json())

export default function EntryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  // Use the search endpoint to fetch a single entry by id — the backend
  // doesn't expose a single-entry JSON API, but we can search by id prefix.
  // Alternatively we use the /api/search endpoint. Since the backend has no
  // /api/entry/:id endpoint, we fetch all and filter client-side.
  // This is acceptable for the current scale (< 1000 entries).
  const { data: entries, error, isLoading } = useSWR<KBEntry[]>(
    '/kb/api/search?q=.',
    fetcher,
  )

  const entry = entries?.find((e) => e.id === id)

  async function handleDelete() {
    if (!id) return
    const confirmed = window.confirm('Delete this entry? This cannot be undone.')
    if (!confirmed) return

    setIsDeleting(true)
    setDeleteError(null)
    try {
      await deleteEntry(id)
      navigate('/kb', { replace: true })
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Delete failed')
      setIsDeleting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-950 text-gray-400">
        <span className="text-sm">Loading…</span>
      </div>
    )
  }

  if (error || (!isLoading && !entry)) {
    return (
      <div className="flex flex-col items-center justify-center h-64 bg-gray-950 text-gray-400 gap-4">
        <p className="text-sm">{error ? 'Failed to load entry.' : 'Entry not found.'}</p>
        <Link to="/kb" className="text-blue-400 hover:underline text-sm">
          &larr; Back to Knowledge Base
        </Link>
      </div>
    )
  }

  if (!entry) return null

  return (
    <div className="bg-gray-950 text-gray-100 p-4 overflow-y-auto min-h-full">
      {/* Back nav */}
      <Link
        to="/kb"
        className="text-gray-500 hover:text-gray-300 text-sm mb-4 inline-block"
      >
        &larr; Back to Knowledge Base
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold break-words">{entry.title}</h1>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className={`text-xs px-1.5 py-0.5 rounded border ${domainBadgeClass(entry.domain)}`}>
              {entry.domain}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded border ${confidenceBadgeClass(entry.confidence)}`}>
              {entry.confidence}
            </span>
            {entry.source_type && (
              <span className="text-xs px-1.5 py-0.5 rounded border border-gray-700 text-gray-400">
                {entry.source_type}
              </span>
            )}
            {entry.tags.map((tag) => (
              <span key={tag} className="text-xs text-gray-500">#{tag}</span>
            ))}
          </div>
        </div>
        <div className="text-right text-sm text-gray-500 shrink-0">
          <div>ID: <code className="text-xs bg-gray-800 px-1 py-0.5 rounded">{entry.id}</code></div>
          <div>Created: {formatDate(entry.created)}</div>
          {entry.expires && <div>Expires: {entry.expires}</div>}
        </div>
      </div>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Summary */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-3">Summary</h2>
            <p className="text-gray-300 leading-relaxed">{entry.summary}</p>
          </div>

          {/* Key Takeaways */}
          {entry.key_takeaways && entry.key_takeaways.length > 0 && (
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-3">Key Takeaways</h2>
              <ul className="space-y-2">
                {entry.key_takeaways.map((takeaway, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-blue-400 mt-0.5">•</span>
                    <span className="text-gray-300">{takeaway}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Context / When to Apply */}
          {entry.context && (
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-3">When to Apply</h2>
              <p className="text-gray-300 leading-relaxed">{entry.context}</p>
            </div>
          )}
        </div>

        {/* Sidebar (1 col) */}
        <div className="space-y-6">
          {/* Metadata */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-3">Metadata</h2>
            <dl className="space-y-2 text-sm">
              <dt className="text-gray-500">Domain</dt>
              <dd className="font-medium">{entry.domain}</dd>
              <dt className="text-gray-500 mt-2">Confidence</dt>
              <dd className="font-medium">{entry.confidence}</dd>
              {entry.source_type && (
                <>
                  <dt className="text-gray-500 mt-2">Source Type</dt>
                  <dd className="font-medium">{entry.source_type}</dd>
                </>
              )}
              {entry.source && (
                <>
                  <dt className="text-gray-500 mt-2">Source</dt>
                  <dd>
                    <a
                      href={entry.source}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:underline text-xs break-all"
                    >
                      {entry.source}
                    </a>
                  </dd>
                </>
              )}
              {entry.tags.length > 0 && (
                <>
                  <dt className="text-gray-500 mt-2">Tags</dt>
                  <dd className="flex flex-wrap gap-1">
                    {entry.tags.map((tag) => (
                      <span
                        key={tag}
                        className="bg-gray-900 px-2 py-0.5 rounded text-xs text-gray-400"
                      >
                        #{tag}
                      </span>
                    ))}
                  </dd>
                </>
              )}
            </dl>
          </div>

          {/* Actions */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-3">Actions</h2>
            {deleteError && (
              <p className="text-xs text-red-400 mb-2">{deleteError}</p>
            )}
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="w-full px-3 py-2 text-sm bg-red-900/60 hover:bg-red-800/60 text-red-300 border border-red-700 rounded transition-colors disabled:opacity-50"
              aria-label="Delete this knowledge base entry"
            >
              {isDeleting ? 'Deleting…' : 'Delete Entry'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
